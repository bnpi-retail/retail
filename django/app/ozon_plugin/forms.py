from django import forms


class EmailForm(forms.Form):
    email = forms.EmailField(label='Введите email от аккаунта Odoo')


class FileUploadForm(forms.Form):
    file = forms.FileField()


class ApiToken(forms.Form):
    token = forms.CharField(label='API Token', max_length=100)