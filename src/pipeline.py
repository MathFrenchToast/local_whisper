import importlib
import os
import sys
import glob
from typing import List, Dict, Any
from src.interfaces import ProcessingStep

class Pipeline:
    def __init__(self):
        self.steps: List[ProcessingStep] = []

    def add_step(self, step: ProcessingStep):
        """Add a processing step to the pipeline."""
        print(f"Pipeline: Added step '{step.name}'")
        self.steps.append(step)

    async def run(self, text: str, context: Dict[str, Any] = None) -> str:
        """
        Pass the text through all registered steps in order.
        """
        if context is None:
            context = {}

        current_text = text
        for step in self.steps:
            try:
                # Pass data to the step
                current_text = await step.process(current_text, context)
                
                # Safety check: ensure plugin returns string
                if not isinstance(current_text, str):
                    print(f"Warning: Step '{step.name}' returned non-string data. Reverting to previous state.")
                    return text
                    
            except Exception as e:
                print(f"Error in pipeline step '{step.name}': {e}")
                # We choose to continue with the previous text rather than crashing
                continue
                
        return current_text

    def load_plugins_from_folder(self, folder_path: str):
        """
        Dynamically load python files from a folder and register valid ProcessingSteps.
        """
        if not os.path.isdir(folder_path):
            return

        # Ensure folder is importable
        if folder_path not in sys.path:
            sys.path.append(folder_path)

        # List .py files
        module_files = glob.glob(os.path.join(folder_path, "*.py"))
        
        for file_path in module_files:
            module_name = os.path.basename(file_path)[:-3] # strip .py
            if module_name.startswith("__"):
                continue
                
            try:
                # Import module dynamically
                # We assume the folder is a package or simply in path
                # Since we added folder_path to sys.path, we can import module_name directly
                module = importlib.import_module(module_name)
                
                # Scan for classes inheriting from ProcessingStep
                for attribute_name in dir(module):
                    attribute = getattr(module, attribute_name)
                    if (isinstance(attribute, type) and 
                        issubclass(attribute, ProcessingStep) and 
                        attribute is not ProcessingStep):
                        
                        # Instantiate and add
                        step_instance = attribute()
                        self.add_step(step_instance)
                        
            except Exception as e:
                print(f"Failed to load plugin {module_name}: {e}")
