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
        public async Task<IActionResult> Index(
            string? category, string? size, string? color,
            decimal? minPrice, decimal? maxPrice, string? sortBy,
            int pageNumber = 1, int pageSize = 12)
        {
            var query = _context.Products
                .Include(p => p.ProductSizes)
                .AsQueryable();

            // Apply filters
            if (!string.IsNullOrEmpty(category))
            {
                query = query.Where(p => p.Category.ToLower() == category.ToLower());
            }

            if (!string.IsNullOrEmpty(size))
            {
                query = query.Where(p => p.ProductSizes.Any(s => s.Size == size && s.Quantity > 0));
            }

            if (!string.IsNullOrEmpty(color) && Enum.TryParse<Color>(color, true, out var colorEnum))
            {
                query = query.Where(p => p.AvailableColors.Contains(colorEnum));
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

            // Get total count before pagination
            var totalCount = await query.CountAsync();

            // Ensure page number is valid
            if (pageNumber < 1) pageNumber = 1;
            var totalPages = (int)Math.Ceiling((double)totalCount / pageSize);
            if (pageNumber > totalPages && totalPages > 0) pageNumber = totalPages;

            // Apply pagination
            var products = await query
                .Skip((pageNumber - 1) * pageSize)
                .Take(pageSize)
                .ToListAsync();

            var viewModel = new ProductListViewModel
            {
                Products = products,
                TotalCount = totalCount,
                CurrentPage = pageNumber,
                PageSize = pageSize,
                SelectedCategory = category,
                SelectedSize = size,
                SelectedColor = color,
                MinPrice = minPrice,
                MaxPrice = maxPrice,
                SortBy = sortBy ?? "featured"
            };

            return View(viewModel);
        }

        // GET: Products/Details/5 (Product Detail Page)
        public async Task<IActionResult> Details(int id)
        {
            var product = await _context.Products
                .Include(p => p.ProductSizes)
                .FirstOrDefaultAsync(p => p.Id == id);

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