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
        public List<CartItem> Items { get; set; } = new List<CartItem>();
    }

    public class Order
    {
        public int Id { get; set; }
        public string OrderNumber { get; set; } = string.Empty;
        public DateTime OrderDate { get; set; }
        public string CustomerId { get; set; } = string.Empty;
        public string CustomerName { get; set; } = string.Empty;
        public string CustomerEmail { get; set; } = string.Empty;

        // Shipping Info
        public string ShippingAddressLine1 { get; set; } = string.Empty;
        public string? ShippingAddressLine2 { get; set; }
        public string ShippingCity { get; set; } = string.Empty;
        public string ShippingState { get; set; } = string.Empty;
        public string ShippingZipCode { get; set; } = string.Empty;
        public string ShippingCountry { get; set; } = string.Empty;

        // Payment Info
        public string PaymentMethod { get; set; } = string.Empty;
        public string? TransactionId { get; set; }

        // Pricing
        public decimal Subtotal { get; set; }
        public decimal ShippingCost { get; set; }
        public decimal Tax { get; set; }
        public decimal Discount { get; set; }
        public decimal Total { get; set; }

        // Status
        public string Status { get; set; } = "Pending"; // Pending, Processing, Shipped, Delivered, Cancelled
        public DateTime? ShippedDate { get; set; }
        public DateTime? DeliveredDate { get; set; }
        public string? TrackingNumber { get; set; }

        // Items
        public List<OrderItem> OrderItems { get; set; } = new List<OrderItem>();
    }

    public class OrderItem
    {
        public int Id { get; set; }
        public int OrderId { get; set; }
        public int ProductId { get; set; }
        public string ProductName { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public int Quantity { get; set; }
        public string? Color { get; set; }
        public string? Size { get; set; }
        public string? ImageUrl { get; set; }

        public decimal TotalPrice => Price * Quantity;
    }

    public class DashboardViewModel
    {
        public string UserName { get; set; } = string.Empty;
        public string UserEmail { get; set; } = string.Empty;
        public int TotalOrders { get; set; }
        public int PendingOrders { get; set; }
        public decimal TotalSpent { get; set; }
        public List<Order> RecentOrders { get; set; } = new List<Order>();
        public ShippingAddress? DefaultAddress { get; set; }
    }
}