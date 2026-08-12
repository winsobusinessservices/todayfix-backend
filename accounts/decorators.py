# from django.contrib.auth.decorators import login_required
# from django.core.exceptions import PermissionDenied


# def admin_required(view_func):

#     @login_required
#     def wrapper(request, *args, **kwargs):

#         if request.user.role != "ADMIN":
#             raise PermissionDenied

#         return view_func(request, *args, **kwargs)

#     return wrapper


# def business_required(view_func):

#     @login_required
#     def wrapper(request, *args, **kwargs):

#         if request.user.role != "BUSINESS":
#             raise PermissionDenied

#         return view_func(request, *args, **kwargs)

#     return wrapper
