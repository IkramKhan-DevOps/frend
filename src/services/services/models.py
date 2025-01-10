import uuid

from cities_light.models import City, Region, Country
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.template.defaultfilters import slugify
from django_ckeditor_5.fields import CKEditor5Field

from src.services.users.models import User, ServiceProvider


class ServiceCategory(models.Model):
    """Service Category Model"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    name = models.CharField(max_length=100, unique=True, help_text="Unique category name.")
    thumbnail = models.ImageField(upload_to='services/categories/', null=True, blank=True,
                                  help_text='Recommended size: 250x250.')
    description = models.TextField(blank=True, null=True, help_text="Small description of the category.")
    is_active = models.BooleanField(default=True, help_text="Indicates if the category is currently active.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['name'], name="unique_service_category_name")
        ]


class ServiceCurrency(models.Model):
    """Service Currency Model"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    name = models.CharField(max_length=100, unique=True, help_text="Unique currency name.")
    code = models.CharField(max_length=3, unique=True, help_text="Unique currency code.")
    symbol = models.CharField(max_length=5, unique=True, help_text="Unique currency symbol.")
    description = models.TextField(blank=True, null=True, help_text="Small description of the currency.")
    is_active = models.BooleanField(default=True, help_text="Indicates if the currency is currently active.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Service Currencies"
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(fields=['name'], name="unique_service_currency_name")
        ]


class Service(models.Model):
    PRICE_TYPE_CHOICES = [
        ('fixed', 'Fixed'),
        ('hourly', 'Hourly'),
    ]
    SERVICE_TYPE_CHOICES = [
        ('onside', 'Onsite'),
        ('online', 'Online'),
        ('both', 'Both'),
    ]

    """Represents a service provided by service providers"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    provider = models.ForeignKey(User, on_delete=models.CASCADE, related_name='services')
    title = models.CharField(max_length=255, help_text="Service title (max 255 characters).")
    slug = models.SlugField(max_length=255, unique=True, help_text="Unique slug for the service.")
    thumbnail = models.ImageField(upload_to='services/thumbnails/', null=True, blank=True,
                                  help_text='Recommended size: 250x250.')
    category = models.ForeignKey(ServiceCategory, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='services', help_text="The category this service belongs to.")
    service_type = models.CharField(max_length=10, choices=SERVICE_TYPE_CHOICES, default='onside',
                                    help_text="The type of service (onsite, online, or both).")
    description = models.TextField(null=True, blank=True, help_text="Small description for your project")
    content = CKEditor5Field(
        'Text', config_name='extends', null=True, blank=True, help_text="Full description for your project"
    )

    price_type = models.CharField(max_length=10, choices=PRICE_TYPE_CHOICES, default='fixed',
                                  help_text="The type of pricing for the service.")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)],
                                help_text="Service price (up to 10 digits and 2 decimal places).")
    currency = models.ForeignKey(ServiceCurrency, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='services',
                                 help_text="The currency for the service price(e.g.,Lira, USD, EUR, etc.).")
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00,
                                   validators=[MinValueValidator(0.00), MaxValueValidator(99.00)]
                                   )

    is_active = models.BooleanField(default=True, help_text="Indicates if the service is available for booking.")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.title} by {self.provider.username}"

    class Meta:
        ordering = ['title']
        constraints = [
            models.UniqueConstraint(fields=['provider', 'title'], name="unique_service_per_provider")
        ]

    def save(self, *args, **kwargs):
        base_slug = slugify(self.title)
        category_slug = slugify(self.category.name) if self.category else ''
        provider_slug = slugify(self.provider.username)
        self.slug = '-'.join(filter(None, [base_slug, category_slug, provider_slug]))

        # Ensure the slug is unique
        if Service.objects.filter(slug=self.slug).exists():
            self.slug = f"{self.slug}-{uuid.uuid4().hex[:5]}"

        super().save(*args, **kwargs)

    def get_discounted_price(self):
        return round(self.price - (self.price * (self.discount / 100)), 2)

    def get_total_rating(self):
        reviews = self.reviews.filter(is_active=True)
        total_rating = sum([review.rating for review in reviews])
        return total_rating

    def get_service_schedule(self):
        return self.availability_slots.filter(is_active=True)


class ServiceImage(models.Model):
    """Service Image Model"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='services/images/', help_text='Recommended size: 800x600.')
    is_active = models.BooleanField(default=True, help_text="Indicates if the service is available for booking.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Image for {self.service.title}"


class ServiceAvailability(models.Model):
    """Service availability slots for providers"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='availability_slots')

    day_of_week = models.CharField(max_length=10, help_text="Day of the week (e.g., Monday).")
    start_time = models.TimeField(help_text="Start time of availability.")
    end_time = models.TimeField(help_text="End time of availability.")
    timezone = models.CharField(max_length=50, default="UTC",
                                help_text="Timezone for the availability slot.")  # New attribute

    is_active = models.BooleanField(default=True, help_text="Is this availability slot active?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Availabilities"
        ordering = ['day_of_week', 'start_time']
        constraints = [
            models.UniqueConstraint(fields=['service', 'day_of_week', 'start_time'], name="unique_service_availability")
        ]

    def __str__(self):
        return f"{self.service.title} available on {self.day_of_week} from {self.start_time} to {self.end_time}"


class ServiceLocation(models.Model):
    """Service location for providers"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='location')
    address = models.CharField(max_length=255, help_text="Service location address.")
    city = models.ForeignKey(City, on_delete=models.SET_NULL, null=True, blank=True, related_name="service_locations")
    region = models.ForeignKey(Region, on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="service_locations")
    country = models.ForeignKey(Country, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="service_locations")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                   help_text="Latitude of the service location.")
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True,
                                    help_text="Longitude of the service location.")
    is_active = models.BooleanField(default=True, help_text="Is this service location active?")

    class Meta:
        verbose_name_plural = "Service Locations"
        ordering = ['city', 'region', 'country']

    def __str__(self):
        return f"{self.service.title} located at {self.address}, {self.city}, {self.region}, {self.country}"


class ServiceReview(models.Model):
    """Stores reviews for services"""
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='given_reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)], help_text="Rating (1-5).")
    comment = models.TextField(blank=True, null=True, help_text="Optional review comment.")
    is_active = models.BooleanField(default=True, help_text="Is this ServiceReview active?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review for {self.service.title} by {self.reviewer.username}"

    class Meta:
        ordering = ['-created_at']
        constraints = [
            models.UniqueConstraint(fields=['service', 'reviewer'], name="unique_service_review_per_user")
        ]


class ServiceAdvertisement(models.Model):
    """Stores advertisements for services"""
    SERVICE_TYPES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
    ]
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    service_type = models.CharField(max_length=20, choices=SERVICE_TYPES, default='online')
    service = models.CharField(max_length=255, help_text="Service Name or Category")
    start_datetime = models.DateTimeField(
        help_text="The starting date and time for the service.",
        null=True, blank=True
    )
    end_datetime = models.DateTimeField(
        help_text="The ending date and time for the service.",
        null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.service} for {self.service.title}"

    class Meta:
        ordering = ['service']


class ServiceAdvertisementRequest(models.Model):
    """Stores requests for services"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
    ]
    advertisement = models.ForeignKey(ServiceAdvertisement, on_delete=models.CASCADE)
    service_provider = models.ForeignKey(ServiceProvider, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.advertisement.service} - {self.service_provider}"

    def get_service_name(self):
        return self.advertisement.service


class ServiceBookingRequest(models.Model):
    """Tracks requests made for services"""
    REQUEST_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('canceled', 'Canceled'),
    ]

    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_requests')
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='requests')
    start_datetime = models.DateTimeField(
        help_text="The starting date and time for the service.",
        null=True, blank=True
    )
    end_datetime = models.DateTimeField(
        help_text="The ending date and time for the service.",
        null=True, blank=True
    )
    message = models.TextField(blank=True, null=True, help_text="Additional notes for the request.")

    status = models.CharField(max_length=20, choices=REQUEST_STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s request for {self.service.title}"


class ServiceOrder(models.Model):
    """Tracks Orders made for services"""
    PAYMENT_TYPE_CHOICES = [
        ('full', 'Full Payment'),
        ('partial', 'Partial Payment'),
    ]
    ORDER_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='service_payments')

    service_booking_request = models.ForeignKey(ServiceBookingRequest, on_delete=models.SET_NULL, null=True, blank=True,
                                                related_name='service_booking_request')
    service_advertisement_request = models.ForeignKey(ServiceAdvertisementRequest, on_delete=models.SET_NULL, null=True,
                                                      blank=True, related_name='service_advertisement_request')

    payment_type = models.CharField(max_length=50, choices=PAYMENT_TYPE_CHOICES, default='full',
                                    help_text="Payment type for the service payment.")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    paid_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tip = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    order_status = models.CharField(max_length=20, choices=ORDER_STATUS_CHOICES, default='pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s order for {self.get_service}"
    def remaining_price(self):
        return self.total_price - self.paid_price

    @property
    def get_service(self):
        return self.service_booking_request.service if self.service_booking_request else self.service_advertisement_request.service


class ServicePayment(models.Model):
    payment_methods = [
        ('credit_card', 'Credit Card'),
        ('debit_card', 'Debit Card'),
        ('by_cash', 'By Cash'),
    ]
    user = models.ForeignKey('users.User', on_delete=models.CASCADE)
    order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE)

    amount = models.DecimalField(max_digits=10, decimal_places=2)
    service_charges = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    tax = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    payment_method = models.CharField(max_length=20, choices=payment_methods, default='credit_card')

    billing_first_name = models.CharField(max_length=255, blank=True, null=True)
    billing_last_name = models.CharField(max_length=255, blank=True, null=True)
    billing_address = models.TextField(blank=True, null=True)
    billing_city = models.CharField(max_length=255, blank=True, null=True)
    billing_state = models.CharField(max_length=255, blank=True, null=True)
    billing_zip = models.CharField(max_length=255, blank=True, null=True)
    billing_country = models.CharField(max_length=255, blank=True, null=True)
    billing_phone = models.CharField(max_length=20, blank=True, null=True)
    billing_email = models.EmailField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user} - {self.order} - {self.amount}"

    class Meta:
        ordering = ['-created_at']


class FavoriteService(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='favorites',
        help_text="The user who added the service to their favorites."
    )
    service = models.ForeignKey(
        Service, on_delete=models.CASCADE, related_name='favorited_by',
        help_text="The service that was added to favorites."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'service')
        ordering = ['-created_at']
        verbose_name = 'Favorite'
        verbose_name_plural = 'Favorites'

    def __str__(self):
        return f"{self.user.username} favorited {self.service.title}"
