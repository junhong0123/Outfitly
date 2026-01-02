using Microsoft.AspNetCore.Identity;

namespace Outfitly.Models
{
    public class Order
    {
        public int Id { get; set; }
        public string UserId { get; set; } = string.Empty;
        public decimal TotalAmount { get; set; }
        public DateTime OrderDate { get; set; } = DateTime.UtcNow;
        public string Status { get; set; } = "Pending"; // Pending, Shipped, Delivered, Cancelled
        public string ShippingAddress { get; set; } = string.Empty;

        // Navigation properties
        public IdentityUser? User { get; set; }
        public ICollection<OrderItem> OrderItems { get; set; } = new List<OrderItem>();
    }
}
