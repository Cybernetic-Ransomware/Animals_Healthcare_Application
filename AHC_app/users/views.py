from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .forms import UserRegisterForm, ProfileUpdateForm, UserUpdateForm


def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)

        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account\s been created for {username}!')
            return redirect('login')
    else:
        form = UserRegisterForm()

    return render(request, 'users/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        user_form = UserRegisterForm(request.POST, instance=request.user)
        profile_update = ProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)

        if user_form.is_valid() and profile_update.is_valid():
            user_form.save()
            profile_update.save()
            messages.success(request, 'Your profile has been updated')
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_update = ProfileUpdateForm(instance=request.user.profile)

    return render(request, 'users/profile.html', {'user_form': user_form, 'profile_update': profile_update})
