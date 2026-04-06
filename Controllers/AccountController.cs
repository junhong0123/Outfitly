using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using Outfitly.Data;
using Outfitly.Models;

namespace Outfitly.Controllers
{
    [Authorize]
    public class AccountController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<IdentityUser> _userManager;

        public AccountController(ApplicationDbContext context, UserManager<IdentityUser> userManager)
        {
            _context = context;
            _userManager = userManager;
        }

        // GET: Account/Orders
        public async Task<IActionResult> Orders(string? status = null, int page = 1)
        {
            var userId = _userManager.GetUserId(User);
            if (string.IsNullOrEmpty(userId))
            {
                return RedirectToAction("Login", "Account", new { area = "Identity" });
            }

            var pageSize = 5;
            var query = _context.Orders
                .Include(o => o.OrderItems)
                .Where(o => o.CustomerId == userId);

            if (!string.IsNullOrEmpty(status) && status.ToLower() != "all")
            {
                query = query.Where(o => o.Status.ToLower() == status.ToLower());
            }

            var totalOrders = await query.CountAsync();
            var totalPages = (int)Math.Ceiling(totalOrders / (double)pageSize);

            // Ensure page is within valid range
            page = Math.Max(1, Math.Min(page, totalPages > 0 ? totalPages : 1));

            var orders = await query
                .OrderByDescending(o => o.OrderDate)
                .Skip((page - 1) * pageSize)
                .Take(pageSize)
                .ToListAsync();

            ViewBag.CurrentPage = page;
            ViewBag.TotalPages = totalPages;
            ViewBag.CurrentStatus = status ?? "all";

            return View(orders);
        }



        // POST: Account/BuyAgain
        [HttpPost]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> BuyAgain(int orderId)
        {
            var userId = _userManager.GetUserId(User);
            if (string.IsNullOrEmpty(userId)) return Unauthorized();

            var order = await _context.Orders
                .Include(o => o.OrderItems)
                .FirstOrDefaultAsync(o => o.Id == orderId && o.CustomerId == userId);

            if (order == null) return NotFound();

            // Add items to cart
            foreach (var item in order.OrderItems)
            {
                var existingCartItem = await _context.CartItems
                    .FirstOrDefaultAsync(c => c.UserId == userId && c.ProductId == item.ProductId && c.Size == item.Size && c.Color == item.Color);

                if (existingCartItem != null)
                {
                    existingCartItem.Quantity += 1;
                    _context.Update(existingCartItem);
                }
                else
                {
                    var product = await _context.Products.FindAsync(item.ProductId);
                    if (product != null)
                    {
                        var newItem = new CartItem
                        {
                            UserId = userId,
                            ProductId = product.Id,
                            ProductName = product.Name,
                            Price = product.Price,
                            Quantity = 1,
                            Size = item.Size,
                            Color = item.Color,
                            ImageUrl = product.ImageUrls?.FirstOrDefault()
                        };
                        _context.CartItems.Add(newItem);
                    }
                }
            }

            await _context.SaveChangesAsync();
            return RedirectToAction("Index", "Cart");
        }

        // GET: Account/WriteReview/{productId}
        public async Task<IActionResult> WriteReview(int productId)
        {
            var userId = _userManager.GetUserId(User);
            if (string.IsNullOrEmpty(userId)) return RedirectToAction("Login", "Account", new { area = "Identity" });

            var product = await _context.Products.FindAsync(productId);
            if (product == null) return NotFound();

            ViewBag.ProductName = product.Name;
            ViewBag.ProductId = product.Id;

            return View(); // Assumes a WriteReview.cshtml view exists
        }

        // GET: Account/OrderDetails/{id}
        public async Task<IActionResult> OrderDetails(int id)
        {
            var userId = _userManager.GetUserId(User);
            if (string.IsNullOrEmpty(userId)) return RedirectToAction("Login", "Account", new { area = "Identity" });

            var order = await _context.Orders
                .Include(o => o.OrderItems)
                .FirstOrDefaultAsync(o => o.Id == id && o.CustomerId == userId);

            if (order == null)
            {
                return NotFound();
            }

            return View(order);
        }

        // POST: Account/WriteReview
        [HttpPost]
        [ValidateAntiForgeryToken]
        public IActionResult WriteReview(int productId, int rating, string reviewText)
        {
            // Placeholder: In a real app, save review to database
            TempData["SuccessMessage"] = "Thank you for your review!";
            return RedirectToAction(nameof(Orders));
        }

        // POST: Account/CancelOrder
        [HttpPost]
        public async Task<IActionResult> CancelOrder(int orderId)
        {
            var userId = _userManager.GetUserId(User);
            var order = await _context.Orders
                .FirstOrDefaultAsync(o => o.Id == orderId && o.CustomerId == userId);

            if (order == null || (order.Status != "Pending" && order.Status != "Processing"))
            {
                return Json(new { success = false, message = "Order cannot be cancelled." });
            }

            order.Status = "Cancelled";
            _context.Update(order);
            await _context.SaveChangesAsync();

            return Json(new
            {
                success = true,
                message = "Order cancelled successfully. Refund will be processed within 3-5 business days."
            });
        }

        // POST: Account/TrackOrder
        [HttpPost]
        public IActionResult TrackOrder(int orderId)
        {
            // Placeholder: Get actual tracking information from shipping provider
            var trackingInfo = new
            {
                trackingNumber = "TRK123456789",
                carrier = "Express Shipping",
                status = "Out for Delivery",
                estimatedDelivery = DateTime.Now.AddDays(2).ToString("MMM dd, yyyy"),
                updates = new[]
                {
                    new { date = "Nov 08, 2025 - 10:30 AM", location = "Local Facility", status = "Out for Delivery" },
                    new { date = "Nov 07, 2025 - 3:45 PM", location = "Distribution Center", status = "In Transit" },
                    new { date = "Nov 06, 2025 - 9:20 AM", location = "Origin Facility", status = "Picked Up" }
                }
            };

            return Json(new { success = true, tracking = trackingInfo });
        }

        // GET: Account/Dashboard
        public async Task<IActionResult> Dashboard()
        {
            var userId = _userManager.GetUserId(User);
            if (string.IsNullOrEmpty(userId))
            {
                return RedirectToAction("Login", "Account", new { area = "Identity" });
            }

            var user = await _userManager.FindByIdAsync(userId);
            if (user == null)
            {
                return RedirectToAction("Login", "Account", new { area = "Identity" });
            }

            var orders = await _context.Orders
                .Where(o => o.CustomerId == userId)
                .OrderByDescending(o => o.OrderDate)
                .ToListAsync();

            var defaultAddress = await _context.SavedAddresses
                .FirstOrDefaultAsync(a => a.UserId == userId);

            var dashboardData = new DashboardViewModel
            {
                UserName = user.UserName ?? user.Email ?? "User",
                UserEmail = user.Email ?? "",
                TotalOrders = orders.Count,
                PendingOrders = orders.Count(o => o.Status == "Pending" || o.Status == "Processing"),
                TotalSpent = orders.Sum(o => o.Total),
                RecentOrders = orders.Take(3).ToList(),
                DefaultAddress = defaultAddress != null ? new ShippingAddress
                {
                    FirstName = defaultAddress.FirstName,
                    LastName = defaultAddress.LastName,
                    AddressLine1 = defaultAddress.AddressLine1,
                    AddressLine2 = defaultAddress.AddressLine2,
                    City = defaultAddress.City,
                    StateProvince = defaultAddress.State,
                    ZipPostalCode = defaultAddress.Zip,
                    Country = defaultAddress.Country,
                    PhoneNumber = defaultAddress.Phone,
                    Email = defaultAddress.Email
                } : null
            };

            return View(dashboardData);
        }

        // Sample orders for testing
        private List<Order> GetSampleOrders()
        {
            return new List<Order>
            {
                new Order
                {
                    Id = 1,
                    OrderNumber = "#12345",
                    OrderDate = new DateTime(2025, 11, 1),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Processing",
                    Subtotal = 356.00m,
                    ShippingCost = 10.00m,
                    Tax = 35.60m,
                    Total = 401.60m,
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 1,
                            ProductName = "Minimal Cotton Tee",
                            Price = 49.00m,
                            Quantity = 1,
                            Color = "Black",
                            Size = "M"
                        },
                        new OrderItem
                        {
                            ProductId = 2,
                            ProductName = "Tailored Linen Pants",
                            Price = 89.00m,
                            Quantity = 2,
                            Color = "Blue",
                            Size = "L"
                        }
                    }
                },
                new Order
                {
                    Id = 2,
                    OrderNumber = "#12344",
                    OrderDate = new DateTime(2025, 10, 28),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Shipped",
                    Subtotal = 129.00m,
                    ShippingCost = 0m,
                    Tax = 12.90m,
                    Total = 141.90m,
                    ShippedDate = new DateTime(2025, 11, 5),
                    TrackingNumber = "TRK123456789",
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 3,
                            ProductName = "Leather Crossbody Bag",
                            Price = 129.00m,
                            Quantity = 1,
                            Color = "Brown",
                            Size = "One Size"
                        }
                    }
                },
                new Order
                {
                    Id = 3,
                    OrderNumber = "#12343",
                    OrderDate = new DateTime(2025, 10, 20),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Delivered",
                    Subtotal = 249.00m,
                    ShippingCost = 0m,
                    Tax = 24.90m,
                    Total = 273.90m,
                    ShippedDate = new DateTime(2025, 10, 22),
                    DeliveredDate = new DateTime(2025, 10, 25),
                    TrackingNumber = "TRK987654321",
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 4,
                            ProductName = "Classic Wool Coat",
                            Price = 249.00m,
                            Quantity = 1,
                            Color = "Gray",
                            Size = "M"
                        }
                    }
                },
                new Order
                {
                    Id = 4,
                    OrderNumber = "#12342",
                    OrderDate = new DateTime(2025, 10, 15),
                    CustomerName = "John Doe",
                    CustomerEmail = "john@example.com",
                    Status = "Cancelled",
                    Subtotal = 79.00m,
                    ShippingCost = 10.00m,
                    Tax = 7.90m,
                    Total = 96.90m,
                    ShippingAddressLine1 = "123 Main Street",
                    ShippingCity = "New York",
                    ShippingState = "NY",
                    ShippingZipCode = "10001",
                    ShippingCountry = "United States",
                    OrderItems = new List<OrderItem>
                    {
                        new OrderItem
                        {
                            ProductId = 5,
                            ProductName = "Silk Blend Blouse",
                            Price = 79.00m,
                            Quantity = 1,
                            Color = "White",
                            Size = "S"
                        }
                    }
                }
            };
        }
    }
}