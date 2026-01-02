namespace Outfitly.Models
{
    public class Product
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public string? Description { get; set; }
        public string? ImageUrl { get; set; }
        public string Category { get; set; } = string.Empty;
        public int Stock { get; set; } // Renamed from StockQuantity to match schema

        // Navigation properties
        public ICollection<OrderItem> OrderItems { get; set; } = new List<OrderItem>();
        public ICollection<CartItem> CartItems { get; set; } = new List<CartItem>();
        public ICollection<UserInteraction> UserInteractions { get; set; } = new List<UserInteraction>();
    }
}
