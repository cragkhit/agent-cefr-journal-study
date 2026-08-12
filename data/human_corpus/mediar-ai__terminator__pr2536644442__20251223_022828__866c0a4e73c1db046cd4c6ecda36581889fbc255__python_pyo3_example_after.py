# `pip install -e .`
# or `maturin develop`

import asyncio
import terminator

class DesktopAutomation:
    def __init__(self):
        # Initialize with all features enabled
        self.desktop = terminator.Desktop.with_all_features()

    async def get_system_info(self):
        root = self.desktop.root()
        print('System Root:', {
            'role': root.role(),
            'name': root.name(),
            'bounds': root.bounds()
        })

    async def list_applications(self):
        apps = self.desktop.applications()
        print('\nRunning Applications:')
        for app in apps:
            attrs = app.attributes()
            print(f"- {attrs.name or 'unnamed'} ({attrs.role})")
            if app.is_focused():
                print('  * Currently focused')

    async def find_and_interact_with_element(self, selector):
        print(f'\nSearching for element: {selector}')
        locator = self.desktop.locator(selector)
        
        try:
            # Wait for element with timeout
            element = await locator.wait(5000)
            attrs = await locator.attributes(5000)
            print('Found element:', {
                'role': attrs.role,
                'name': attrs.name,
                'label': attrs.label,
                'value': attrs.value,
                'description': attrs.description,
                'properties': attrs.properties,
                'is_keyboard_focusable': attrs.is_keyboard_focusable
            })

            # Check if element is visible and enabled
            if await locator.is_visible():
                print('Element is visible')
                enabled_element = await locator.expect_enabled()
                if enabled_element:
                    print('Element is enabled')
                    
                    # Try to click the element
                    click_result = await locator.click()
                    print('Click result:', {
                        'method': click_result.method,
                        'coordinates': click_result.coordinates,
                        'details': click_result.details
                    })

                    # Try double click
                    double_click_result = await locator.double_click()
                    print('Double click result:', {
                        'method': double_click_result.method,
                        'coordinates': double_click_result.coordinates,
                        'details': double_click_result.details
                    })

                    # Try right click
                    await locator.right_click()
                    print('Right click performed')

                    # Try hover
                    await locator.hover()
                    print('Hover performed')

                    # Get text content
                    text = await locator.text(max_depth=30)
                    print('Element text:', text)

                    # Get bounds
                    bounds = await locator.bounds()
                    print('Element bounds:', bounds)

        except terminator.ElementNotFoundError as e:
            print('Element not found:', str(e))
        except terminator.TimeoutError as e:
            print('Timeout waiting for element:', str(e))
        except Exception as e:
            print('Error interacting with element:', str(e))

    async def capture_and_analyze_screen(self):
        try:
            # Capture screen
            screenshot = await self.desktop.capture_screen()
            print('\nScreenshot captured:', {
                'dimensions': f'{screenshot.width}x{screenshot.height}',
                'size': f'{len(screenshot.image_data)} bytes'
            })

            # Perform OCR on the screenshot
            text = await self.desktop.ocr_screenshot(screenshot)
            print('\nOCR Result:', text)
        except Exception as e:
            print('Screenshot/OCR failed:', str(e))

    async def work_with_current_window(self):
        try:
            # Get current window
            window = await self.desktop.get_current_window()
            attrs = window.attributes()
            print('\nCurrent Window:', {
                'role': attrs.role,
                'name': attrs.name,
                'bounds': window.bounds()
            })

            # Get current application
            app = await self.desktop.get_current_application()
            attrs = app.attributes()
            print('Current Application:', {
                'role': attrs.role,
                'name': attrs.name
            })

            # Get focused element
            focused = self.desktop.focused_element()
            attrs = focused.attributes()
            print('Focused Element:', {
                'role': attrs.role,
                'name': attrs.name
            })

            # Get browser window
            try:
                browser = await self.desktop.get_current_browser_window()
                attrs = browser.attributes()
                print('Current Browser Window:', {
                    'role': attrs.role,
                    'name': attrs.name
                })
            except terminator.ElementNotFoundError:
                print('No browser window found')

        except terminator.ElementNotFoundError as e:
            print('No window found - this is normal if no window is focused')
        except Exception as e:
            print('Error getting window info:', str(e))

    async def run_system_command(self):
        try:
            # Use cmd.exe /c to properly expand environment variables
            cmd = await self.desktop.run_command(
                windows_command='cmd.exe /c echo %USERNAME%',
                unix_command='echo $USER'
            )
            print('\nCommand Output:', {
                'exitStatus': cmd.exit_status,
                'stdout': cmd.stdout.strip(),
                'stderr': cmd.stderr
            })
        except Exception as e:
            print('Command failed:', str(e))

    async def open_and_activate_app(self, app_name):
        try:
            print(f'\nOpening application: {app_name}')
            self.desktop.open_application(app_name)
            
            # Wait a bit for the app to start
            await asyncio.sleep(2)
            
            print(f'Activating application: {app_name}')
            self.desktop.activate_application(app_name)

            # Wait for the application to be fully activated
            await asyncio.sleep(1)
        except Exception as e:
            print(f'Error with application {app_name}:', str(e))

    async def open_url_and_file(self):
        try:
            # Open a URL in the default browser
            print('\nOpening URL in browser')
            self.desktop.open_url('https://www.example.com', None)

            # Wait a bit for the browser to open
            await asyncio.sleep(2)

            # Open a file with its default application
            print('Opening file with default application')
            self.desktop.open_file('test.txt')

            # Wait a bit for the file to open
            await asyncio.sleep(2)

            # Activate browser window by title
            print('Activating browser window')
            self.desktop.activate_browser_window_by_title('Example Domain')

        except Exception as e:
            print('Error opening URL/file:', str(e))

    async def advanced_element_operations(self):
        try:
            # Find a window by criteria
            print('\nFinding window by criteria')
            window = await self.desktop.find_window_by_criteria('Notepad', 5000)
            attrs = window.attributes()
            print('Found window:', {
                'role': attrs.role,
                'name': attrs.name
            })

            # Create a locator within the window
            locator = self.desktop.locator('role:button').within(window)
            
            # Wait for element to be visible
            element = await locator.expect_visible(5000)
            attrs = element.attributes()
            print('Found visible element:', {
                'role': attrs.role,
                'name': attrs.name
            })

            # Wait for specific text
            element = await locator.expect_text_equals('Close', max_depth=30, timeout_ms=30000)
            attrs = element.attributes()
            print('Found element with text:', {
                'role': attrs.role,
                'name': attrs.name
            })

        except terminator.ElementNotFoundError as e:
            print('Element not found:', str(e))
        except terminator.TimeoutError as e:
            print('Timeout waiting for element:', str(e))
        except Exception as e:
            print('Error in advanced operations:', str(e))

async def main():
    automation = DesktopAutomation()
    
    # Get system information
    await automation.get_system_info()
    
    # List all running applications
    await automation.list_applications()
    
    # Work with current window and focused elements
    await automation.work_with_current_window()
    
    # Find and interact with elements
    await automation.find_and_interact_with_element('role:button')
    await automation.find_and_interact_with_element('name:Close')
    
    # Capture and analyze screen
    await automation.capture_and_analyze_screen()
    
    # Run a system command
    await automation.run_system_command()
    
    # Try to open and activate an application
    await automation.open_and_activate_app('notepad')

    # Open URL and file
    await automation.open_url_and_file()

    # Advanced element operations
    await automation.advanced_element_operations()

if __name__ == "__main__":
    asyncio.run(main()) 