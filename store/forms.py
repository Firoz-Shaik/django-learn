from django import forms
from .models import ReviewRating

class ReviewForm(forms.ModelForm):
    class Meta:
        model = ReviewRating
        fields = ['subject', 'review', 'rating']

    def clean_rating(self):
        rating = self.cleaned_data['rating']
        if rating < 0.5 or rating > 5 or rating * 2 != int(rating * 2):
            raise forms.ValidationError('Choose a rating from 0.5 to 5 stars in half-star steps.')
        return rating