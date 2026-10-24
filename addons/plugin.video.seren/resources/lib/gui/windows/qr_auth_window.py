from resources.lib.gui.windows.base_window import BaseWindow

CONTROL_CANCEL = 200


class QRAuthWindow(BaseWindow):
    """
    Displays a scannable QR code alongside a verification URL/code for
    device-code OAuth flows. Purely a display surface - the caller drives
    the polling loop from the main thread while this window runs doModal()
    on its own thread, updating properties/the QR image as state changes
    and closing the window when done.
    """

    def __init__(self, xml_file, location):
        super().__init__(xml_file, location)
        self.canceled_by_user = False

    def set_title(self, title_text):
        self.setProperty("qrauth.title", title_text or "")

    def set_qr_image(self, image_path):
        self.setProperty("qrauth.image", image_path or "")

    def set_details(self, url_text, code_text):
        self.setProperty("qrauth.url", url_text)
        self.setProperty("qrauth.code", code_text)

    def set_status(self, status_text):
        self.setProperty("qrauth.status", status_text)

    def onAction(self, action):
        if action.getId() in self.action_exitkeys_id:
            self.canceled_by_user = True
        super().onAction(action)

    def handle_action(self, action_id, control_id=None):
        if action_id == 7 and control_id == CONTROL_CANCEL:
            self.canceled_by_user = True
            self.close()
