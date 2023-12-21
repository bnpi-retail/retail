from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.views import View

from .forms import CustomUserCreationForm
from .models import CustomUser
        

class GetAPIView(View):
    template_name = 'accounts/get_api.html'

    def get(self, request):
        form = CustomUserCreationForm()
        return render(request, self.template_name, {'form': form})
    
    def post(self, request):
        form = CustomUserCreationForm(request.POST)

        email = request.POST.get('email')
        user_exists = CustomUser.objects.filter(email=email).exists()

        if user_exists:
            user = authenticate(email=email, password=form.standart_password)
            if user:
                login(request, user)
                messages.success(request, f'You have been logged in successfully!')
                return redirect('home')

        if form.is_valid():
            user = form.save()
            user = authenticate(email=email, password=form.standart_password)
            messages.success(request, f'Account created for {user.email}!')
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            return render(request, self.template_name, {'form': form})



