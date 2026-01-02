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
        public async Task<IActionResult> Index(string? category, decimal? minPrice, decimal? maxPrice, string? sortBy)
        {
            // Query products from database
            var productsQuery = _context.Products.AsQueryable();

            // Apply filters
            if (!string.IsNullOrEmpty(category))
            {
                productsQuery = productsQuery.Where(p => p.Category.Equals(category, StringComparison.OrdinalIgnoreCase));
            }

            if (minPrice.HasValue)
            {
                productsQuery = productsQuery.Where(p => p.Price >= minPrice.Value);
            }

            if (maxPrice.HasValue)
            {
                productsQuery = productsQuery.Where(p => p.Price <= maxPrice.Value);
            }

            // Apply sorting
            productsQuery = sortBy switch
            {
                "newest" => productsQuery.OrderByDescending(p => p.Id),
                "price-low" => productsQuery.OrderBy(p => p.Price),
                "price-high" => productsQuery.OrderByDescending(p => p.Price),
                "popular" => productsQuery.OrderByDescending(p => p.Id),
                _ => productsQuery // featured (default)
            };

            var products = await productsQuery.ToListAsync();

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
            var product = await _context.Products.FirstOrDefaultAsync(p => p.Id == id);

            if (product == null)
            {
                return NotFound();
            }

            // AI Prep: Log user interaction for "View" event if user is authenticated
            if (User.Identity != null && User.Identity.IsAuthenticated)
            {
                var userId = User.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;

                if (!string.IsNullOrEmpty(userId))
                {
                    var interaction = new UserInteraction
                    {
                        UserId = userId,
                        ProductId = id,
                        InteractionType = "View",
                        TimeStamp = DateTime.UtcNow
                    };

                    _context.UserInteractions.Add(interaction);
                    await _context.SaveChangesAsync();
                }
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
