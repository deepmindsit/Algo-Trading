from fastapi.templating import Jinja2Templates

class AppTemplates():
    def getMailTemplates():
        templates = Jinja2Templates(directory="templates/email")
        return templates
