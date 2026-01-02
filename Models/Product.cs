namespace Outfitly.Models
{
    public class Product
    {
        public int Id { get; set; }
        public string Name { get; set; } = string.Empty;
        public decimal Price { get; set; }
        public string? ImageUrl { get; set; }
        public string? Description { get; set; }
        public string Category { get; set; } = string.Empty;
        public List<string> AvailableColors { get; set; } = new List<string>();
        public List<string> AvailableSizes { get; set; } = new List<string>();
        public int StockQuantity { get; set; }
        public DateTime CreatedAt { get; set; } = DateTime.Now;
    }
}
