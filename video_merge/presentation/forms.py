from __future__ import annotations

from pathlib import Path

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from video_merge.domain.constants import SUPPORTED_VIDEO_EXTENSIONS


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data, initial=None) -> list[object]:
        single_file_clean = super().clean

        if data in self.empty_values:
            raise forms.ValidationError("En az bir video dosyasi secin.")

        if isinstance(data, (list, tuple)):
            return [single_file_clean(file_obj, initial) for file_obj in data]

        return [single_file_clean(data, initial)]


class MergeJobCreateForm(forms.Form):
    name = forms.CharField(
        max_length=150,
        required=False,
        label="Is adi",
        widget=forms.TextInput(attrs={"placeholder": "Ornek: Saha Kamerasi - Pazartesi"}),
    )
    files = MultipleFileField(
        label="Video dosyalari",
        widget=MultipleFileInput(
            attrs={
                "accept": ",".join(SUPPORTED_VIDEO_EXTENSIONS),
            }
        ),
    )

    def clean_files(self) -> list[object]:
        files = self.cleaned_data.get("files", [])
        if not files:
            raise forms.ValidationError("En az bir video dosyasi secin.")

        for uploaded in files:
            extension = Path(uploaded.name).suffix.lower()
            if extension not in SUPPORTED_VIDEO_EXTENSIONS:
                raise forms.ValidationError(f"Desteklenmeyen dosya uzantisi: {extension}")

        return files


class SignUpForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")
