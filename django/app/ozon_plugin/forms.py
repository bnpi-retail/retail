from django import forms


class EmailForm(forms.Form):
    email = forms.EmailField(label='Введите email от аккаунта Odoo')

class FileUploadForm(forms.Form):
    file = forms.FileField()