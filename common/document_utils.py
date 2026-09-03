"""
Shared helper for streaming uploaded files (images/documents)
through a Django view, so responses never depend on a raw
/media/ URL (which Django only serves at all when DEBUG=True).

Callers are responsible for their own permission checks BEFORE
calling this - this function only handles safely streaming
whichever FieldFile it's given.
"""

import mimetypes

from django.http import FileResponse, Http404


def serve_document_file(file_field, download_name=None):
    """
    Stream a Django FieldFile (FileField/ImageField value) as an
    inline HTTP response, so browsers preview PDFs/images directly
    instead of force-downloading them.

    Returns a 404 response if no file is attached.
    """
    if not file_field:
        raise Http404("No file has been uploaded for this field.")

    try:
        file_handle = file_field.open("rb")
    except (FileNotFoundError, ValueError):
        # FieldFile references a path but the file isn't on disk
        # (e.g. deleted manually, or storage moved) - fail cleanly
        # rather than crashing with a 500.
        raise Http404("This file could not be found.")

    name_for_lookup = download_name or file_field.name

    content_type, _ = mimetypes.guess_type(name_for_lookup)
    content_type = content_type or "application/octet-stream"

    response = FileResponse(
        file_handle,
        content_type=content_type,
        as_attachment=False,  # inline = view in browser, not force-download
        filename=name_for_lookup.split("/")[-1],
    )

    return response