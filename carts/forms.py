from django import forms


class CheckoutForm(forms.Form):
    first_name = forms.CharField(max_length=50, label="First name")
    last_name = forms.CharField(max_length=50, label="Last name")
    email = forms.EmailField(label="Email")
    phone_number = forms.CharField(max_length=20, label="Phone number")
    address_line_1 = forms.CharField(max_length=100, label="Address line 1")
    address_line_2 = forms.CharField(max_length=100, label="Address line 2", required=False)
    city = forms.CharField(max_length=50)
    state = forms.CharField(max_length=50)
    country = forms.CharField(max_length=50)
    zip_code = forms.CharField(max_length=20, label="Zip code")
    order_note = forms.CharField(
        label="Order note",
        required=False,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
