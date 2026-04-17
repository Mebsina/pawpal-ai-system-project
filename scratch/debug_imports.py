import sys
import os

print(f"Current Working Directory: {os.getcwd()}")
print(f"Python Path: {sys.path}")

try:
    import ai
    print(f"ai location: {ai.__file__}")
    import ai.tools
    print(f"ai.tools location: {ai.tools.__file__}")
    from ai.tools.add_task import add_task_tool
    print("Successfully imported add_task_tool")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
