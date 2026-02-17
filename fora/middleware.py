from django.conf import settings
from django.http import HttpResponse, HttpResponseRedirect


class SharedPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        self.password = getattr(settings, "SITE_PASSWORD", "")

    def __call__(self, request):
        if not self.password:
            return self.get_response(request)

        if request.session.get("authenticated"):
            return self.get_response(request)

        if request.method == "POST" and request.path == "/login/":
            if request.POST.get("password") == self.password:
                request.session["authenticated"] = True
                return HttpResponseRedirect("/")
            return self._login_page(error="Wrong password")

        return self._login_page()

    def _login_page(self, error=""):
        html = f"""<!DOCTYPE html>
<html><head><title>Login</title>
<style>
body {{ font-family: sans-serif; display: flex; justify-content: center; align-items: center; height: 100vh; margin: 0; background: #f5f5f5; }}
form {{ background: white; padding: 2rem; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
input[type=password] {{ display: block; width: 100%; padding: 0.5rem; margin: 0.5rem 0 1rem; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }}
button {{ padding: 0.5rem 1.5rem; background: #333; color: white; border: none; border-radius: 4px; cursor: pointer; }}
.error {{ color: red; font-size: 0.9rem; }}
</style></head>
<body><form method="post" action="/login/">
<h2>Password</h2>
{'<p class="error">' + error + '</p>' if error else ''}
<input type="password" name="password" autofocus>
<button type="submit">Enter</button>
</form></body></html>"""
        response = HttpResponse(html)
        response["Content-Type"] = "text/html"
        return response
