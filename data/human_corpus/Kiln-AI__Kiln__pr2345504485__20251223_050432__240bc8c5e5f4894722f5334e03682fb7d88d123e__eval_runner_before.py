import asyncio
from dataclasses import dataclass
from typing import AsyncGenerator, List

from kiln_ai.adapters.eval.base_eval import BaseEval
from kiln_ai.adapters.eval.registry import eval_adapter_from_type
from kiln_ai.datamodel.dataset_filters import dataset_filter_from_id
from kiln_ai.datamodel.eval import EvalConfig
from kiln_ai.datamodel.task import TaskRunConfig
from kiln_ai.datamodel.task_run import TaskRun


@dataclass
class EvalJob:
    item: TaskRun
    task_run_config: TaskRunConfig


@dataclass
class EvalProgress:
    complete: int | None = None
    total: int | None = None
    errors: int | None = None


class EvalRunner:
    """
    Runs an eval.

    Specifically, runs a specific eval config on a list of task runs.
    """

    def __init__(
        self,
        eval_config: EvalConfig,
        run_configs: List[TaskRunConfig],
    ):
        # confirm these are compatible
        target_eval = eval_config.parent_eval()
        if target_eval is None:
            raise ValueError("Eval config requires a parent eval")
        target_task = target_eval.parent_task()
        if target_task is None:
            raise ValueError("Eval config requires a (grand)parent task")
        if len(run_configs) == 0:
            raise ValueError("Eval config requires at least one run config")

        # confirm the run configs are for the target task
        for run_config in run_configs:
            parent_task = run_config.parent_task()
            if parent_task is None:
                raise ValueError("Each run config requires a parent task")
            if parent_task.id != target_task.id:
                raise ValueError(
                    "Run config is not for the same task as the eval config"
                )

        self.eval_config = eval_config
        self.run_configs = run_configs
        self.task = target_task
        self.eval = target_eval

    def collect_tasks(self) -> List[EvalJob]:
        """
        Collect all jobs for this run, excluding any that have already been run.

        The tasks:
        - should be in one of the eval filters: the eval filter (what's being evaluated) or the eval config filter (what's being evaluated to compare eval configs).
        - should not have already been run for this eval config
        """
        config_filter = dataset_filter_from_id(self.eval.eval_configs_filter_id)
        eval_filter = dataset_filter_from_id(self.eval.eval_set_filter_id)

        already_run = {
            f"{run.dataset_id}::{run.task_run_config_id}"
            for run in self.eval_config.runs(readonly=True)
        }
        return [
            EvalJob(item=task_run, task_run_config=run_config)
            for task_run in self.task.runs(readonly=True)
            if config_filter(task_run) or eval_filter(task_run)
            for run_config in self.run_configs
            if f"{task_run.id}::{run_config.id}" not in already_run
        ]

    async def run(self, concurrency: int = 25) -> AsyncGenerator[EvalProgress, None]:
        """
        Runs the eval with parallel workers and yields progress updates.
        """
        jobs = self.collect_tasks()

        complete = 0
        errors = 0
        total = len(jobs)

        # Send initial status
        yield EvalProgress(complete=complete, total=total, errors=errors)

        worker_queue: asyncio.Queue[EvalJob] = asyncio.Queue()
        for job in jobs:
            worker_queue.put_nowait(job)

        # simple status queue to return progress. True=success, False=error
        status_queue: asyncio.Queue[bool] = asyncio.Queue()

        workers = []
        for i in range(concurrency):
            task = asyncio.create_task(self.run_worker(worker_queue, status_queue))
            workers.append(task)

        # Send status updates until workers are done, and they are all sent
        while not status_queue.empty() or not all(worker.done() for worker in workers):
            try:
                # Use timeout to prevent hanging if all workers complete
                # between our while condition check and get()
                success = await asyncio.wait_for(status_queue.get(), timeout=0.1)
                if success:
                    complete += 1
                else:
                    errors += 1

                yield EvalProgress(complete=complete, total=total, errors=errors)
            except asyncio.TimeoutError:
                # Timeout is expected, just continue to recheck worker status
                # Don't love this but beats sentinels for reliability
                continue

        # These are redundant, but keeping them will catch async errors
        await asyncio.gather(*workers)
        await worker_queue.join()

    async def run_worker(
        self, worker_queue: asyncio.Queue[EvalJob], status_queue: asyncio.Queue[bool]
    ):
        while True:
            try:
                job = worker_queue.get_nowait()
            except asyncio.QueueEmpty:
                # worker can end when the queue is empty
                break
            try:
                success = await self.run_job(job)
                await status_queue.put(success)
            finally:
                # Always mark the dequeued task as done, even on exceptions
                worker_queue.task_done()

    async def run_job(self, job: EvalJob) -> bool:
        try:
            # Create the evaluator for this eval config/run config pair
            evaluator = eval_adapter_from_type(self.eval_config.config_type)(
                self.eval_config, job.task_run_config.run_config()
            )
            if not isinstance(evaluator, BaseEval):
                raise ValueError("Not able to create evaluator from eval config")

            task_run, scores = await evaluator.run(job.item.input)
            print(f"Result: {task_run.id} {scores}")

            return True
        except Exception as e:
            print(f"Error running job: {e}")
            return False
