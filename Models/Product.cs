namespace Outfitly.Models
{
    public class Product
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public List<string> ImageUrls { get; set; } = new List<string>();
        public string? Description { get; set; }
        public string Category { get; set; } = string.Empty;
        public List<Color> AvailableColors { get; set; } = new List<Color>();
        public ICollection<ProductSize> ProductSizes { get; set; } = new List<ProductSize>();
        public int TotalQuantity => ProductSizes?.Sum(s => s.Quantity) ?? 0;
        public DateTime CreatedAt { get; set; } = DateTime.Now;
    }
}
