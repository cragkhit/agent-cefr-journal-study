"""Math Animation Code Generator

This module implements a CodeGenerator for generating manim code for mathematical concepts.
It uses a large language model to generate manim code for a given mathematical concept.
"""

import logging
import os
from datetime import datetime
from typing import Dict

from datasets import load_dataset, load_from_disk

import argparse
from bespokelabs import curator

# ruff: noqa

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", handlers=[logging.FileHandler("manim_generation.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


class ManimCodeGenerator(curator.LLM):
    """Generates manim code for mathematical concepts"""

    # response_format = ManimCode

    def prompt(self, input: Dict) -> str:
        # Extract key information from the input
        subject = input.get("subject", "Mathematics")
        topic = input.get("topic", "General")
        question = input.get("question", "")
        title = input.get("title", "Mathematical Concept")
        narration = input.get("narration", "")
        visual_elements = input.get("visual_elements", [])
        equations = input.get("equations", [])
        key_timestamps = input.get("key_timestamps", [])
        visual_style = input.get("visual_style", "")

        # Format visual elements for prompt
        visual_elements_text = ""
        for i, element in enumerate(visual_elements):
            element_name = element.get("name", f"Element {i+1}")
            element_desc = element.get("description", "")
            visual_elements_text += f"- {element_name}: {element_desc}\n"

        # Format equations for prompt
        equations_text = "\n".join([f"- {eq}" for eq in equations])

        # Format key timestamps for prompt
        timestamps_text = "\n".join([f"- {ts}" for ts in key_timestamps])

        return f"""
        Create a simple, executable manim code for a basic animation explaining the following mathematical concept:
        
        SUBJECT: {subject}
        TOPIC: {topic}
        QUESTION: {question}
        TITLE: {title}
        
        NARRATION:
        {narration}
        
        KEY VISUAL ELEMENTS TO INCLUDE:
        {visual_elements_text}
        
        EQUATIONS TO ANIMATE:
        {equations_text}
        
        KEY TIMESTAMPS:
        {timestamps_text}
        
        VISUAL STYLE:
        {visual_style}
        
        REQUIREMENTS:
        1. Create a simple, self-contained Python script using the manim library
        2. The code should define a main Scene class that inherits from Scene
        3. Focus on BASIC animations - text, simple shapes, and 1-2 equations
        4. Keep the animation short (30-60 seconds when rendered)
        5. Include appropriate comments to explain the code
        6. The code must run with a standard manim installation
        7. DO NOT use placeholder code or comments like "# Add implementation here"
        8. The output video should be named "video.mp4"
        
        SIMPLIFICATION GUIDELINES:
        - Use only basic manim objects (Text, MathTex, Circle, Square, Arrow, etc.)
        - Limit to 2-3 simple animations (Create, FadeIn, Write, Transform)
        - Avoid complex camera movements or 3D visualizations
        - Use at most 1-2 equations that are central to the concept
        - Keep all animations sequential (one after another)
        - Avoid complex custom functions or classes
        
        The python_code field should contain complete, executable manim code as a string with proper indentation and formatting.
        Focus on SIMPLICITY over complexity - a working simple animation is better than a complex one that might not work.

        Your output should be in the following format:

        ```scene_class_name
        /// Your scene class name here
        ```

        ```initial_code
        /// Your initial code here
        ```

        ```verification_notes
        /// Your verification notes here. Verify if there is anything wrong with the code.
        ```

        ```python
        /// Your final code here. It should be inside the ```python``` tags. If there are any corrections needed, make them here.
        ```
        """

    def parse(self, input: Dict, response: Dict) -> Dict:
        # Extract information from the concept for the result
        #

        title = input.get("title", "Mathematical Concept")
        # Create a sanitized filename from the title
        sanitized_title = title.lower().replace(" ", "_")
        sanitized_title = "".join(c for c in sanitized_title if c.isalnum() or c == "_")

        # Generate code to render the animation
        return {
            **input,
            # Pass through original concept information
            "concept_id": input.get("id", None),
            # Add manim code information
            "python_code": response.split("```python")[1].split("```")[0].strip(),
            "scene_class_name": response.split("```scene_class_name")[1].split("```")[0].strip(),
            # Add metadata
            "generation_time": datetime.now().strftime("%Y%m%d_%H%M%S"),
            "filename": f"{sanitized_title}.py",
        }


def generate_manim_codes(dataset_path, output_dir="manim_code"):
    """Generate manim code for all concepts in a dataset at once

    Args:
        dataset_path: Path to the concepts dataset
        output_dir: Directory to save generated code

    Returns:
        Path to the directory with generated code
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    code_dir = os.path.join(output_dir, "python_files")
    os.makedirs(code_dir, exist_ok=True)

    # Load the dataset
    dataset = load_from_disk(dataset_path)
    logger.info(f"Loaded dataset with {len(dataset)} concepts")

    # Initialize the code generator
    code_generator = ManimCodeGenerator(model_name="anthropic/claude-3-7-sonnet-20250219", generation_params={"max_tokens": 32768})

    # Generate code for all concepts in a single pass
    logger.info(f"Generating manim code for all {len(dataset)} concepts at once")
    results_dataset = code_generator(dataset)

    # Save the dataset with code
    results_dataset.push_to_hub("pimpalgaonkar/manim_codes_10k_full", private=True)

    # Save individual Python files


def main(dataset_name, output_dataset_name):
    """Verify concepts by generating code for a few samples

    Args:
        dataset_path: Path to the concepts dataset
        num_samples: Number of samples to test

    Returns:
        List of sample results
    """
    # Load the dataset
    dataset = load_dataset(dataset_name)

    os.environ["HOSTED_CURATOR_VIEWER"] = "1"
    # Initialize the code generator
    code_generator = ManimCodeGenerator(model_name="claude-3-7-sonnet-20250219", generation_params={"max_tokens": 37286}, batch=True)

    # Generate code for samples
    results = code_generator(dataset)

    # save to hf
    results.push_to_hub(output_dataset_name, private=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset_name", type=str, default="pimpalgaonkar/math_scripts")
    parser.add_argument("--output_dataset_name", type=str, default="pimpalgaonkar/manim_codes_10k_full")
    args = parser.parse_args()

    sample_results = main(args.dataset_name, args.output_dataset_name)
