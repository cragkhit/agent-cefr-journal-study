"""
Preprocess dataset for sokoban task - see rage/env/sokoban/sokoban.py for details
"""

import re
import os
import json
from datasets import Dataset, load_dataset
from random import randint, seed, choice
from typing import List, Tuple
from tqdm import tqdm
from verl.utils.hdfs_io import copy, makedirs
import argparse
import datasets

from ragen.policy.bfs import BFSPolicy
from ragen.policy.heuristic import FixedPolicy
from ragen.env.sokoban import SokobanEnv
from ragen.evaluators.trajectory_evaluator import TrajectoryEvaluator
# from ragen.utils.dataset import Dataset

templates = {
    'qwen-instruct': '<|im_start|>system\nYou are a helpful assistant. <|im_end|>\n<|im_start|>user\n{prompt}\nAlways output: <think> [Your thoughts] </think> <answer> [your answer] </answer> with no extra text. Strictly follow this format. <|im_end|>\n<|im_start|>assistant\n<think>',
    'base': 'A conversation between User and Assistant. The user asks a question, and the Assistant solves it. The assistant first thinks briefly about the reasoning process in the mind and then provides the user with the answer.\nUser: {prompt}\nShow your work in <think> </think> tags. And return the final answer in <answer> </answer> tags, for example <think> [Thoughts] </think> <answer> 1 </answer>\nAssistant: \n<think>'
}

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Generate trajectories using specified environment and policy.")
    parser.add_argument("--env", type=str, default="sokoban", help="Environment name (default: 'sokoban').")
    parser.add_argument("--algo", type=str, default="bfs", choices=["bfs"], help="Algorithm to use (default: 'bfs').")
    parser.add_argument("--seed", type=int, default=10000, help="Seed for random number generation (default: 10000).")
    parser.add_argument("--output", type=str, default="data/sokoban", help="Output file to save the trajectories (default: 'data/sokoban').")
    parser.add_argument("--train_size", type=int, default=300, help="Number of trajectories to generate (default: 3000).")
    parser.add_argument("--test_size", type=int, default=10, help="Number of trajectories to generate (default: 100).")
    parser.add_argument("--bfs_max_nodes", type=int, default=1000, help="Maximum number of nodes to use for BFS (default: 100000).") # not using this now. This will usually give the best traj. To compare with SFT, we will try this later.
    parser.add_argument("--prefix", type=str, default='qwen-instruct', choices=['qwen-instruct', 'base'])

    args = parser.parse_args()
    
    assert args.env == "sokoban", "Unsupported environment: {args.env}"
    assert args.algo == "bfs", "Unsupported algorithm: {args.algo}"
    data_source = args.env
    
    dim_x, dim_y, num_boxes, max_steps, search_depth = os.environ.get("DIM_X"), os.environ.get("DIM_Y"), os.environ.get("NUM_BOXES"), os.environ.get("MAX_STEPS"), os.environ.get("SEARCH_DEPTH")
    dim_x, dim_y, num_boxes, max_steps, search_depth = int(dim_x), int(dim_y), int(num_boxes), int(max_steps), int(search_depth)

    env = SokobanEnv(dim_room=(dim_x, dim_y), num_boxes=num_boxes, max_steps=max_steps, search_depth=search_depth)
    policy = FixedPolicy()
    # policy = BFSPolicy(max_nodes=args.bfs_max_nodes)
    evaluator = TrajectoryEvaluator(env, policy, max_steps=1)

    # Generate trajectories
    seeds = range(args.seed, args.seed + args.train_size + args.test_size)
    trajectories = evaluator.batch_evaluate(seeds, mp=True) # mp=False is not working

    # # Print metrics for BFS
    # evaluator.print_metrics()

    # TRAIN_SIZE = args.train_size
    # TEST_SIZE = args.test_size

    # dataset_views = Dataset(trajectories).transform("decision_making")

    # assert len(raw_dataset) > TRAIN_SIZE + TEST_SIZE
    # train_dataset = raw_dataset.select(range(TRAIN_SIZE))
    # test_dataset = raw_dataset.select(range(TRAIN_SIZE, TRAIN_SIZE + TEST_SIZE))

    # dataset just need to provide placeholders
    def _create_instance(idx, traj):
        prompt_formatted = templates[args.prefix].format(prompt=traj[0]['policy_input'])

        return {
            "data_source": data_source,
            "prompt": [{"role": "user", "content": prompt_formatted}],
            "ability": "bfs",
            "reward_model": {"style": "rule", "ground_truth": {"target": 0, "numbers": [0, 0]}},
            "extra_info": {"split": "train", "index": idx}
        }
    train_dataset = Dataset.from_list([_create_instance(args.seed + i, trajectories[i]) for i in range(args.train_size)])
    test_dataset = Dataset.from_list([_create_instance(args.seed + i, trajectories[i]) for i in range(args.train_size, args.train_size + args.test_size)])


    def make_map_fn(split):
        def process_fn(example, idx):
            return example
        return process_fn

    
    train_dataset = train_dataset.map(function=make_map_fn('train'), with_indices=True)
    test_dataset = test_dataset.map(function=make_map_fn('test'), with_indices=True)

    train_dataset.to_parquet(os.path.join(args.output, 'train.parquet'))
    test_dataset.to_parquet(os.path.join(args.output, 'test.parquet'))

if __name__ == "__main__":
    main()