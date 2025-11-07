using Microsoft.AspNetCore.Mvc;
using Outfitly.Models;

namespace Outfitly.Controllers
{
    public class ProductsController : Controller    
    {
        // GET: Products (Product Listing Page)
        public IActionResult Index(string? category, decimal? minPrice, decimal? maxPrice, string? sortBy)
        {
            // TODO: Replace with actual database query
            var products = GetSampleProducts();

            // Apply filters
            if (!string.IsNullOrEmpty(category))
            {
                products = products.Where(p => p.Category.Equals(category, StringComparison.OrdinalIgnoreCase)).ToList();
            }

            if (minPrice.HasValue)
            {
                products = products.Where(p => p.Price >= minPrice.Value).ToList();
            }

            if (maxPrice.HasValue)
            {
                products = products.Where(p => p.Price <= maxPrice.Value).ToList();
            }

            // Apply sorting
            products = sortBy switch
            {
                "newest" => products.OrderByDescending(p => p.Id).ToList(),
                "price-low" => products.OrderBy(p => p.Price).ToList(),
                "price-high" => products.OrderByDescending(p => p.Price).ToList(),
                "popular" => products.OrderByDescending(p => p.Id).ToList(),
                _ => products // featured (default)
            };

            var viewModel = new ProductListViewModel
            {
                Products = products,
                TotalCount = products.Count,
                SelectedCategory = category,
                MinPrice = minPrice,
                MaxPrice = maxPrice,
                SortBy = sortBy ?? "featured"
            };

            return View(viewModel);
        }

        // GET: Products/Details/5 (Product Detail Page)
        public IActionResult Details(int id)
        {
            // TODO: Replace with actual database query
            var product = GetSampleProducts().FirstOrDefault(p => p.Id == id);

            if (product == null)
            {
                return NotFound();
            }

            return View(product);
        }

        // GET: Products/Recommendations (AI Recommendations Page)
        public IActionResult Recommendations()
        {
            // TODO: Implement AI recommendation logic
            var products = GetSampleProducts().Take(8).ToList();
            return View(products);
        }

        // Sample data - Replace with actual database later
        private List<Product> GetSampleProducts()
        {
            return new List<Product>
            {
                new Product
                {
                    Id = 1,
                    Name = "Minimal Cotton Tee",
                    Price = 49.00m,
                    Category = "tops",
                    AvailableColors = new List<string> { "black", "white", "gray" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L", "XL" }
                },
                new Product
                {
                    Id = 2,
                    Name = "Tailored Linen Pants",
                    Price = 89.00m,
                    Category = "bottoms",
                    AvailableColors = new List<string> { "blue", "gray" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" }
                },
                new Product
                {
                    Id = 3,
                    Name = "Leather Crossbody Bag",
                    Price = 129.00m,
                    Category = "accessories",
                    AvailableColors = new List<string> { "brown", "black" },
                    AvailableSizes = new List<string> { "One Size" }
                },
                new Product
                {
                    Id = 4,
                    Name = "Classic Wool Coat",
                    Price = 249.00m,
                    Category = "outerwear",
                    AvailableColors = new List<string> { "gray", "navy" },
                    AvailableSizes = new List<string> { "S", "M", "L" }
                },
                new Product
                {
                    Id = 5,
                    Name = "Silk Blend Blouse",
                    Price = 79.00m,
                    Category = "tops",
                    AvailableColors = new List<string> { "white", "pink" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L" }
                },
                new Product
                {
                    Id = 6,
                    Name = "Denim Jacket",
                    Price = 119.00m,
                    Category = "outerwear",
                    AvailableColors = new List<string> { "blue", "black" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" }
                },
                new Product
                {
                    Id = 7,
                    Name = "Wide Leg Trousers",
                    Price = 95.00m,
                    Category = "bottoms",
                    AvailableColors = new List<string> { "black", "beige" },
                    AvailableSizes = new List<string> { "XS", "S", "M", "L", "XL" }
                },
                new Product
                {
                    Id = 8,
                    Name = "Cashmere Sweater",
                    Price = 159.00m,
                    Category = "tops",
                    AvailableColors = new List<string> { "cream", "gray", "black" },
                    AvailableSizes = new List<string> { "S", "M", "L" }
                },
                new Product
                {
                    Id = 9,
                    Name = "Ankle Boots",
                    Price = 189.00m,
                    Category = "accessories",
                    AvailableColors = new List<string> { "black", "brown" },
                    AvailableSizes = new List<string> { "36", "37", "38", "39", "40" }
                },
                new Product
                {
                    Id = 10,
                    Name = "Oversized Blazer",
                    Price = 199.00m,
                    Category = "outerwear",
                    AvailableColors = new List<string> { "black", "gray", "beige" },
                    AvailableSizes = new List<string> { "S", "M", "L", "XL" }
                }
            };
        }
    }
}