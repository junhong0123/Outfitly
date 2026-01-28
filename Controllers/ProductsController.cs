using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Outfitly.Data;
using Outfitly.Models;

namespace Outfitly.Controllers
{
    public class ProductsController : Controller
    {
        private readonly ApplicationDbContext _context;

        public ProductsController(ApplicationDbContext context)
        {
            _context = context;
        }

        // GET: Products (Product Listing Page)
        public async Task<IActionResult> Index(string? category, string? size, string? color, decimal? minPrice, decimal? maxPrice, string? sortBy)
        {
            var query = _context.Products.AsQueryable();

            // Apply filters
            if (!string.IsNullOrEmpty(category))
            {
                query = query.Where(p => p.Category.ToLower() == category.ToLower());
            }

            if (!string.IsNullOrEmpty(size))
            {
                query = query.Where(p => p.AvailableSizes.Contains(size));
            }

            if (!string.IsNullOrEmpty(color))
            {
                query = query.Where(p => p.AvailableColors.Contains(color));
            }

            if (minPrice.HasValue)
            {
                query = query.Where(p => p.Price >= minPrice.Value);
            }

            if (maxPrice.HasValue)
            {
                query = query.Where(p => p.Price <= maxPrice.Value);
            }

            // Apply sorting
            query = sortBy switch
            {
                "newest" => query.OrderByDescending(p => p.CreatedAt),
                "price-low" => query.OrderBy(p => p.Price),
                "price-high" => query.OrderByDescending(p => p.Price),
                "popular" => query.OrderByDescending(p => p.Id),
                _ => query.OrderBy(p => p.Id) // featured (default)
            };

            var products = await query.ToListAsync();

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
        public async Task<IActionResult> Details(int id)
        {
            var product = await _context.Products.FindAsync(id);

            if (product == null)
            {
                return NotFound();
            }

            return View(product);
        }

        // GET: Products/Recommendations (AI Recommendations Page)
        public async Task<IActionResult> Recommendations()
        {
            // TODO: Implement AI recommendation logic
            var products = await _context.Products.Take(8).ToListAsync();
            return View(products);
        }
    }
}