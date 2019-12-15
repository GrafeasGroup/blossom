from django.shortcuts import redirect

def wiki_media_url_rewrite(get_response):
    # All this does is force the incoming url for media content to redirect to
    # the base domain so that it resolves correctly ¯\_(ツ)_/¯
    def middleware(request):
        if "media" in request.path:
            if "wiki" in request.get_host():
                h = request.get_host()
                return redirect(
                    request.scheme + '://' + h[h.index('.')+1:] + request.path
                )

        response = get_response(request)

        return response

    return middleware
