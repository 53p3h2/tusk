from textual.app import App
from ui.dashboard import Dashboard


class ProcessManagerApp(App):
    TITLE = "Process Manager"
    SUB_TITLE = "TUI Process Manager"
    CSS = """
    Screen {
        background: $surface;
    }
    """

    def compose(self):
        yield Dashboard()

    pass


if __name__ == "__main__":
    ProcessManagerApp().run()
