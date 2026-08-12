import asyncio
import terminator
import os

async def run_notepad():
    desktop = terminator.Desktop(log_level="error") # log_level="error" is used to suppress the info logs
    try:
        print("Opening Notepad...")
        desktop.open_application("notepad.exe")
        await asyncio.sleep(2)

        editor = desktop.locator('window:Notepad')

        print('typing text...')
        await editor.type_text('hello from terminator!\nthis is a python test.')
        await asyncio.sleep(1)

        print('pressing enter...')
        await editor.press_key('{Enter}')
        await asyncio.sleep(1)

        await editor.type_text('done.')

        content = await editor.locator('role:Edit').text()
        print(f'notepad content retrieved: {content}')

        print("Opening Save As dialog...")
        await editor.press_key('{Ctrl}s')

        print("Entering file name...")
        save_dialog = desktop.locator('window:Save As').locator('window:Save As')
        file_name_edit_box = save_dialog.locator('role:Pane').locator('role:ComboBox').locator('role:Edit')

        home_dir = os.path.expanduser('~')
        file_path = os.path.join(home_dir, 'terminator_notepad_test.md')
        await file_name_edit_box.type_text(file_path)
        
        # Get the pane and explore its contents
        pane = save_dialog.locator('role:Pane')
        pane_elements = await pane.explore()
        
        # Find and click the Save as type ComboBox
        # This changes the file type to `All Files` so that we can save it in any file format
        for child in pane_elements.children:
            if child.role == 'ComboBox' and child.suggested_selector and child.name == 'Save as type:':
                combo_box = save_dialog.locator(child.suggested_selector)
                await combo_box.click()
                await combo_box.press_key('{Ctrl}a')
                break
        
        # Find and click the Save button
        window_elements = await save_dialog.explore()
        for child in window_elements.children:
            if child.role == 'Button' and child.suggested_selector and child.name == 'Save':
                save_button = save_dialog.locator(child.suggested_selector)
                await save_button.click()
                break

        # This is a workaround to handle the confirmation dialog that appears when saving a file that already exists
        confirm_overwrite = await save_dialog.explore()
        for child in confirm_overwrite.children:
            if child.role == 'Window' and child.suggested_selector and 'Confirm Save As' in child.text:
                save_button = save_dialog.locator(child.suggested_selector)
                await save_button.locator('Name:Yes').click()
                break

        print("File saved successfully!")

    except terminator.PlatformError as e:
        print(f"Platform Error: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(run_notepad())