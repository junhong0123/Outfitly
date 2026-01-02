// Models/CheckoutViewModel.cs
using Outfitly.Models;
using System.ComponentModel.DataAnnotations;

namespace Outfitly.Models
{
    public class CheckoutViewModel
    {
        public ShippingAddress ShippingAddress { get; set; } = new ShippingAddress();
        public PaymentInfo PaymentInfo { get; set; } = new PaymentInfo();
        public Cart Cart { get; set; } = new Cart();
        public string? PromoCode { get; set; }
        public decimal PromoDiscount { get; set; }

        // Saved addresses (max 3)
        public List<UserAddress> SavedAddresses { get; set; } = new List<UserAddress>();
        public int? SelectedAddressId { get; set; }
        public bool SaveNewAddress { get; set; } = false;
    }

    public class ShippingAddress
    {
        [Required]
        public string FirstName { get; set; } = string.Empty;

        [Required]
        public string LastName { get; set; } = string.Empty;

        [Required]
        [EmailAddress]
        public string Email { get; set; } = string.Empty;

        [Required]
        [Phone]
        public string PhoneNumber { get; set; } = string.Empty;

        [Required]
        public string AddressLine1 { get; set; } = string.Empty;

        public string? AddressLine2 { get; set; }

        [Required]
        public string City { get; set; } = string.Empty;

        [Required]
        public string StateProvince { get; set; } = string.Empty;

        [Required]
        public string ZipPostalCode { get; set; } = string.Empty;

        [Required]
        public string Country { get; set; } = string.Empty;
    }

    public class PaymentInfo
    {
        [Required]
        public string PaymentMethod { get; set; } = "card"; // card, paypal, bank

        [Required]
        public string CardNumber { get; set; } = string.Empty;

        [Required]
        public string CardholderName { get; set; } = string.Empty;

        [Required]
        public string ExpiryDate { get; set; } = string.Empty;

        [Required]
        public string CVV { get; set; } = string.Empty;
    }

    public class OrderConfirmation
    {
        public int OrderId { get; set; }
        public DateTime OrderDate { get; set; }
        public decimal TotalAmount { get; set; }
        public string Status { get; set; } = string.Empty;
        public DateTime EstimatedDelivery { get; set; }
        public ShippingAddress? ShippingAddress { get; set; }
        public List<CartItemViewModel> Items { get; set; } = new List<CartItemViewModel>();
    }

    public class DashboardViewModel
    {
        public string UserName { get; set; } = string.Empty;
        public string UserEmail { get; set; } = string.Empty;
        public int TotalOrders { get; set; }
        public int PendingOrders { get; set; }
        public decimal TotalSpent { get; set; }
        public List<Order> RecentOrders { get; set; } = new List<Order>(); // Uses the database Order model
        public ShippingAddress? DefaultAddress { get; set; }
    }
}