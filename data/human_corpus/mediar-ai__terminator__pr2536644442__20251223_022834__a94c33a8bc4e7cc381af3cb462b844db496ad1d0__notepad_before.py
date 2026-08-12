import logging
import sys
import os
import time

# Add the python-sdk directory to the path to find the terminator_sdk module
SDK_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python-sdk'))
if SDK_PATH not in sys.path:
    sys.path.insert(0, SDK_PATH)

# Now we can import the SDK
from desktop_use import DesktopUseClient, ApiError, ConnectionError, sleep

# --- Configuration --- #
# Optional: Configure logging for more detailed output
# logging.basicConfig(level=logging.DEBUG,
#                     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logging.basicConfig(level=logging.INFO,
                    format='%(levelname)s: %(message)s')

# Ensure the Terminator server (e.g., `cargo run --example server`) is running!

def run_notepad():
    client = DesktopUseClient()
    try:
        print("Opening Notepad...")
        client.open_application("notepad.exe")
        time.sleep(2)  # Wait for Notepad to open

        editor = client.locator('window:Notepad')

        print('typing text...')
        editor.type_text('hello from terminator!\nthis is a python test.')
        time.sleep(1)

        print('pressing enter...')
        editor.press_key('{Enter}')
        time.sleep(1)

        editor.type_text('done.')

        content = editor.get_text()
        print(f'notepad content retrieved: {content.text}')

        print("Opening Save As dialog...")
        editor.press_key('{Ctrl}s')

        print("Entering file name...")
        save_dialog = client.locator('window:Save As').locator('window:Save As')
        file_name_edit_box = save_dialog.locator('role:Pane').locator('role:ComboBox').locator('role:Edit')

        home_dir = os.path.expanduser('~')
        file_path = os.path.join(home_dir, 'terminator_notepad_test.md')
        file_name_edit_box.type_text(file_path)
        
        # Get the pane and explore its contents
        pane = save_dialog.locator('role:Pane')
        pane_elements = pane.explore()
        
        # Find and click the Save as type ComboBox
        # This changes the file type to `All Files` so that we can save it in any file format
        for child in pane_elements.children:
            if child.get('role') == 'ComboBox' and child.get('suggested_selector') and child.get('name') == 'Save as type:':
                combo_box = save_dialog.locator(child['suggested_selector'])
                combo_box.click()
                combo_box.press_key('{Ctrl}a')
                break
        
        # Find and click the Save button
        window_elements = save_dialog.explore()
        for child in window_elements.children:
            if child.get('role') == 'Button' and child.get('suggested_selector') and child.get('text') == 'Save':
                save_button = save_dialog.locator(child['suggested_selector'])
                save_button.click()
                break

        # This is a workaround to handle the confirmation dialog that appears when saving a file that already exists
        confirm_overwrite = save_dialog.explore()
        for child in confirm_overwrite.children:
            if child.get('role') == 'Window' and child.get('suggested_selector') and 'Confirm Save As' in child.get('text'):
                save_button = save_dialog.locator(child['suggested_selector'])
                save_button.locator('Name:Yes').click()
                break

        print("File saved successfully!")

    except ApiError as e:
        print(f"API Status: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    run_notepad()