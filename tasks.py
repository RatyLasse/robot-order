from PIL import Image
from robocorp.tasks import task
from robocorp import browser
from RPA.HTTP import HTTP
from RPA.Tables import Tables
from RPA.PDF import PDF
from RPA.FileSystem import FileSystem
from RPA.Archive import Archive
from RPA.Assistant import Assistant


@task
def order_robots_from_RobotSpareBin():
    """
    Orders robots from RobotSpareBin Industries Inc.
    Saves the order HTML receipt as a PDF file.
    Saves the screenshot of the ordered robot.
    Embeds the screenshot of the robot to the PDF receipt.
    Creates ZIP archive of the receipts and images.
    """
    orders = get_orders()
    order_url = input_order_website()
    for order in orders:
        open_robot_order_website(order_url)
        close_annoying_modal()
        fill_the_form(order)
        get_robot_preview()
        order_number = submit_order()
        store_receipt_as_pdf(order_number)
        embed_screenshot_to_receipt(
            "preview.png", "output/receipts/" + order_number + "_receipt.pdf"
        )
    archive_receipts()
    remove_temp_files()


def input_order_website():
    assistant = Assistant()
    assistant.add_heading("Please input robot order website URL")
    assistant.add_text_input("text_input", placeholder="Please enter URL", default="https://robotsparebinindustries.com/#/robot-order")
    assistant.add_submit_buttons("Submit", default="Submit")
    result = assistant.run_dialog()
    url = result.text_input
    return url


def open_robot_order_website(url):
    """Navigates to the website where orders are input"""
    browser.goto(url)


def get_orders():
    """Downloads the orders csv and returns it in a Table"""
    http = HTTP()
    http.download(url="https://robotsparebinindustries.com/orders.csv", overwrite=True)

    library = Tables()
    orders = library.read_table_from_csv(
        "orders.csv", columns=["Order number", "Head", "Body", "Legs", "Address"]
    )
    return orders


def close_annoying_modal():
    """Closes the modal popup which appears when first navigating to the page by clicking 'I guess so...'"""
    page = browser.page()
    page.click("button:text('I guess so...')")


def fill_the_form(order):
    """Fills the robot order form and clicks preview to see a preview of the robot picture"""
    page = browser.page()
    page.select_option("#head", str(order["Head"]))
    page.check("#id-body-" + str(order["Body"]))
    page.fill(
        'input[placeholder="Enter the part number for the legs"]', str(order["Legs"])
    )
    page.fill("#address", order["Address"])


def get_robot_preview():
    """Gets a screenshot of the robot preview"""
    page = browser.page()
    page.click("#preview")
    for i in range(1, 4):
        page.wait_for_selector(f"#robot-preview-image > :nth-child({i})")
    element = page.locator("#robot-preview-image")
    element.screenshot(path="preview.png")


def submit_order():
    """Clicks submit order and waits for the success message to appear"""
    page = browser.page()

    for _ in range(5):  # Retry up to 5 times
        try:
            page.click("#order")
            page.wait_for_selector(
                "#order-completion", timeout=2000
            )  # Tiny wait stage just for sake of testing. TODO: Wait for error message at the same time
            return page.query_selector(".badge.badge-success").inner_text()
        except Exception:
            print("Order completion element did not appear, retrying...")

    raise Exception("Failed to submit order after 3 attempts")


def store_receipt_as_pdf(order_number):
    """Stores the order completion HTML as PDF"""
    page = browser.page()
    receipt_html = page.locator("#order-completion").inner_html()

    pdf = PDF()
    pdf.html_to_pdf(receipt_html, "output/receipts/" + order_number + "_receipt.pdf")


def embed_screenshot_to_receipt(screenshot, pdf_file):
    """Embed screenshot of the robot to its receipt."""
    pdf = PDF()
    file = [screenshot]
    pdf.add_files_to_pdf(files=file, target_document=pdf_file, append=True)


def archive_receipts():
    """Creates a zip file of all the created receipts"""
    lib = Archive()
    lib.archive_folder_with_zip("./output/receipts", "./output/receipts.zip")


def remove_temp_files():
    """Removes the receipts directory, orders.csv and preview.png when these files are no longer needed"""
    lib = FileSystem()
    lib.remove_directory("./output/receipts", recursive=True)
    lib.remove_files("orders.csv", "preview.png")
