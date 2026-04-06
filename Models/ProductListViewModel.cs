namespace Outfitly.Models
{
    public class ProductListViewModel
    {
        public List<Product> Products { get; set; } = new List<Product>();
        public int TotalCount { get; set; }
        public int CurrentPage { get; set; } = 1;
        public int PageSize { get; set; } = 12;
        public int TotalPages => (int)Math.Ceiling((double)TotalCount / PageSize);

        // Filter properties
        public string? SelectedCategory { get; set; }
        public string? SelectedSize { get; set; }
        public string? SelectedColor { get; set; }
        public decimal? MinPrice { get; set; }
        public decimal? MaxPrice { get; set; }
        public string SortBy { get; set; } = "featured";
    }
}
