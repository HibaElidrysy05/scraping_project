from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages


def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 != password2:
            messages.error(request, "Les mots de passe ne correspondent pas.")
            return redirect("register")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Ce nom d'utilisateur existe déjà.")
            return redirect("register")

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password1
        )

        user.save()

        messages.success(request, "Compte créé avec succès. Vous pouvez vous connecter.")
        return redirect("login")

    return render(request, "register.html")


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect("index")
        else:
            messages.error(request, "Nom d'utilisateur ou mot de passe incorrect.")
            return redirect("login")

    return render(request, "login.html")


def logout_view(request):
    logout(request)
    return redirect("login")

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.contrib.auth.models import User


@api_view(["POST"])
def register_api(request):
    username = request.data.get("username")
    email = request.data.get("email")
    password1 = request.data.get("password1")
    password2 = request.data.get("password2")

    if not username or not password1 or not password2:
        return Response({"error": "Tous les champs obligatoires sont requis."}, status=400)

    if password1 != password2:
        return Response({"error": "Les mots de passe ne correspondent pas."}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Ce nom d'utilisateur existe déjà."}, status=400)

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password1
    )

    return Response({"message": "Compte créé avec succès."})