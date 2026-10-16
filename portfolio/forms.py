from django import forms

from .models import ContactMessage


class ContactForm(forms.ModelForm):
    """Email-only contact form. Submissions are stored privately in the database."""

    # Honeypot: real people never see or fill this field.
    website = forms.CharField(
        required=False,
        label="Leave this field empty",
        widget=forms.TextInput(attrs={"autocomplete": "off", "tabindex": "-1"}),
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "message"]
        labels = {"name": "Your name", "email": "Your email", "message": "Message"}
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name", "maxlength": 120}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "message": forms.Textarea(attrs={"rows": 5, "maxlength": 4000}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("label_suffix", "")
        super().__init__(*args, **kwargs)

    def clean_message(self):
        message = self.cleaned_data["message"].strip()
        if len(message) < 10:
            raise forms.ValidationError("Please write at least a sentence (10 characters).")
        return message

    @property
    def is_spam(self) -> bool:
        return bool(self.data.get("website"))
