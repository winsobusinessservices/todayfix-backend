# from django.shortcuts import render, redirect
# from django.contrib.auth import authenticate, login, logout
# from django.contrib import messages


# from .models import CustomUser, UserRole

# from django.contrib.auth.decorators import login_required
# from directory.models import Business


# def login_choice(request):
#     return render(request, "accounts/login_choice.html")


# def login_view(request):

#     role = request.GET.get("role", "user")

#     # Already logged in
#     if request.user.is_authenticated:

#         if request.user.role == "ADMIN":
#             return redirect("admin_dashboard")

#         elif request.user.role == "BUSINESS":

#             if hasattr(request.user, "business"):

#                 status = request.user.business.status

#                 if status == "APPROVED":
#                     return redirect("business_dashboard")

#                 elif status == "PENDING":
#                     messages.warning(
#                         request,
#                         "Your business is waiting for admin approval."
#                     )

#                 elif status == "REJECTED":
#                     messages.error(
#                         request,
#                         "Your business registration has been rejected."
#                     )

#                 return redirect("login")

#             return redirect("business_register")

#     if request.method == "POST":

#         username = request.POST.get("username")
#         password = request.POST.get("password")

#         user = authenticate(
#             request,
#             username=username,
#             password=password
#         )

#         if user is not None:

#             login(request, user)

#             # ---------------- ADMIN ---------------- #
#             if user.role == "ADMIN":
#                 return redirect("admin_dashboard")

#             # --------------- BUSINESS -------------- #
#             elif user.role == "BUSINESS":

#                 # User has not registered a business yet
#                 if not hasattr(user, "business"):
#                     return redirect("business_register")

#                 business = user.business

#                 # Pending approval
#                 if business.status == "PENDING":
#                     messages.warning(
#                         request,
#                         "Your business registration is waiting for admin approval."
#                     )
#                     return redirect("pending_approval")

#                 # Rejected
#                 if business.status == "REJECTED":
#                     messages.error(
#                         request,
#                         "Your business listing has been rejected. Please contact the administrator."
#                     )
#                     return redirect("pending_approval")

#                 # Approved
#                 if business.status == "APPROVED":
#                     return redirect("business_dashboard")

#                 # Fallback
#                 messages.error(request, "Invalid business status.")
#                 return redirect("login")

#             # ---------------- USER ---------------- #
#             elif user.role == "USER":

#                 return redirect("user_dashboard")

#         messages.error(
#             request,
#             "Invalid username or password."
#         )

#     context = {
#             "role": role,
#         }

    
#     return render(request, "accounts/login.html",context)



# def logout_view(request):

#     logout(request)
#     messages.success(request, "Logged out successfully.")

#     return redirect("login")




# def register_view(request):

#     if request.user.is_authenticated:
#         return redirect("login")

#     if request.method == "POST":

#         name = request.POST.get("name")
#         email = request.POST.get("email")
#         phone = request.POST.get("phone")
#         password = request.POST.get("password")
#         confirm_password = request.POST.get("confirm_password")

#         # Validation
#         if password != confirm_password:
#             messages.error(request, "Passwords do not match.")
#             return redirect("signup")

#         if CustomUser.objects.filter(email=email).exists():
#             messages.error(request, "Email already exists.")
#             return redirect("signup")

#         if CustomUser.objects.filter(phone=phone).exists():
#             messages.error(request, "Phone number already exists.")
#             return redirect("signup")

#         # Create User
#         CustomUser.objects.create_user(
#             name=name,
#             email=email,
#             phone=phone,
#             password=password,
#             role=UserRole.USER
#         )

#         messages.success(
#             request,
#             "Account created successfully. Please login."
#         )

#         return redirect("login")

#     return render(request, "accounts/signup.html")


# @login_required
# def dashboard_redirect(request):

#     # Admin
#     if request.user.role == "ADMIN":
#         return redirect("admin_dashboard")

#     # Business
#     if request.user.role == "BUSINESS":

#         business = Business.objects.filter(user=request.user).first()

#         if business is None:
#             return redirect("business_register")

#         if business.status == "PENDING":
#             return redirect("pending_approval")

#         if business.status == "REJECTED":
#             return redirect("business_rejected")

#         return redirect("business_dashboard")

#     # Normal User
#     if request.user.role == "USER":
#         return redirect("user_dashboard")

#     return redirect("home")


