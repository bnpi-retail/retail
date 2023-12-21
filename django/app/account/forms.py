import requests

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login

from .models import CustomUser
from .services import connect_to_odoo_api_with_auth


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ('email', 'password1', 'password2')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.standart_password = 'b>A9Uk,3gJ?t5%3'

        self.fields['password1'].widget = forms.HiddenInput()
        self.fields['password2'].widget = forms.HiddenInput()
        self.fields['password1'].label = ''
        self.fields['password2'].label = ''
        self.fields['password1'].required = False
        self.fields['password2'].required = False

    def clean_email(self):
        email = self.cleaned_data['email']

        user = CustomUser.objects.filter(email=email).first()
        if user: return email
        
        session_id = connect_to_odoo_api_with_auth()
        if session_id is False: 
            raise forms.ValidationError('Не удалось установить соединение с Odoo.')

        endpoint = "http://odoo-web:8069/get_users"
        headers = {"Cookie": f"session_id={session_id}"}
        response = requests.post(endpoint, headers=headers)

        found_emails = response.json()
        if email not in found_emails:
            raise forms.ValidationError('Такой email не существует в системе Odoo.')
        return email

    def check_user_existence(self):
        email = self.cleaned_data.get('email')
        user = CustomUser.objects.filter(email=email).first()
        return user is not None

    def save(self, commit=True):
        self.cleaned_data['password1'] = self.standart_password
        self.cleaned_data['password2'] = self.standart_password
        return super().save(commit)