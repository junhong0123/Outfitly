// Models/CartItem.cs
namespace Outfitly.Models
{
    public class CartItem
    {
        public int Id { get; set; }
        public int ProductId { get; set; }
        public string ProductName { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public int Quantity { get; set; }
        public string? Color { get; set; }
        public string? Size { get; set; }
        public string? ImageUrl { get; set; }

        // Calculate total price for this item
        public decimal TotalPrice => Price * Quantity;
    }

    public class Cart
    {
        public List<CartItem> Items { get; set; } = new List<CartItem>();

        // Calculate cart subtotal
        public decimal Subtotal => Items.Sum(item => item.TotalPrice);

        // Calculate total items count
        public int TotalItems => Items.Sum(item => item.Quantity);

        // Calculate shipping (example logic)
        public decimal Shipping => Subtotal >= 100 ? 0 : 10.00m;

        // Calculate tax (example: 10%)
        public decimal Tax => Subtotal * 0.10m;

        // Calculate grand total
        public decimal Total => Subtotal + Shipping + Tax;
    }
}