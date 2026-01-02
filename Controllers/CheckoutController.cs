using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Authorization;
using Microsoft.EntityFrameworkCore;
using Outfitly.Data;
using Outfitly.Models;
using System.Security.Claims;

namespace Outfitly.Controllers
{
    public class CheckoutController : Controller
    {
        private readonly ApplicationDbContext _context;
        private readonly UserManager<IdentityUser> _userManager;

        public CheckoutController(ApplicationDbContext context, UserManager<IdentityUser> userManager)
        {
            _context = context;
            _userManager = userManager;
        }

        // GET: Checkout
        [Authorize]
        public async Task<IActionResult> Index()
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                return Redirect("/Identity/Account/Login?ReturnUrl=/Checkout");
            }

            // Get cart items from database
            var cartItems = await _context.CartItems
                .Include(c => c.Product)
                .Where(c => c.UserId == userId)
                .ToListAsync();

            if (!cartItems.Any())
            {
                TempData["Error"] = "Your cart is empty.";
                return RedirectToAction("Index", "Cart");
            }

            // Get saved addresses (max 3)
            var savedAddresses = await _context.UserAddresses
                .Where(a => a.UserId == userId)
                .OrderByDescending(a => a.IsDefault)
                .ThenByDescending(a => a.CreatedAt)
                .Take(3)
                .ToListAsync();

            // Calculate totals
            var cartViewModel = new Cart
            {
                Items = cartItems.Select(c => new CartItemViewModel
                {
                    Id = c.Id,
                    ProductId = c.ProductId,
                    ProductName = c.Product?.Name ?? "Unknown",
                    Price = c.Product?.Price ?? 0,
                    Quantity = c.Quantity,
                    ImageUrl = c.Product?.ImageUrl
                }).ToList()
            };

            var viewModel = new CheckoutViewModel
            {
                Cart = cartViewModel,
                SavedAddresses = savedAddresses
            };

            // Pre-fill with default address if exists
            var defaultAddress = savedAddresses.FirstOrDefault(a => a.IsDefault) ?? savedAddresses.FirstOrDefault();
            if (defaultAddress != null)
            {
                viewModel.SelectedAddressId = defaultAddress.Id;
                viewModel.ShippingAddress = new ShippingAddress
                {
                    FirstName = defaultAddress.FirstName,
                    LastName = defaultAddress.LastName,
                    AddressLine1 = defaultAddress.AddressLine1,
                    AddressLine2 = defaultAddress.AddressLine2,
                    City = defaultAddress.City,
                    StateProvince = defaultAddress.StateProvince,
                    ZipPostalCode = defaultAddress.ZipPostalCode,
                    Country = defaultAddress.Country,
                    PhoneNumber = defaultAddress.PhoneNumber ?? ""
                };
            }

            return View(viewModel);
        }

        // POST: Checkout/PlaceOrder
        [HttpPost]
        [Authorize]
        [ValidateAntiForgeryToken]
        public async Task<IActionResult> PlaceOrder(CheckoutViewModel model)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            if (string.IsNullOrEmpty(userId))
            {
                return Redirect("/Identity/Account/Login");
            }

            // Get cart items from database
            var cartItems = await _context.CartItems
                .Include(c => c.Product)
                .Where(c => c.UserId == userId)
                .ToListAsync();

            if (!cartItems.Any())
            {
                TempData["Error"] = "Your cart is empty.";
                return RedirectToAction("Index", "Cart");
            }

            // Calculate total
            decimal totalAmount = cartItems.Sum(c => (c.Product?.Price ?? 0) * c.Quantity);

            // Save new address if requested and user has less than 3 addresses
            if (model.SaveNewAddress)
            {
                var addressCount = await _context.UserAddresses.CountAsync(a => a.UserId == userId);
                if (addressCount < 3)
                {
                    var newAddress = new UserAddress
                    {
                        UserId = userId,
                        FirstName = model.ShippingAddress.FirstName,
                        LastName = model.ShippingAddress.LastName,
                        AddressLine1 = model.ShippingAddress.AddressLine1,
                        AddressLine2 = model.ShippingAddress.AddressLine2,
                        City = model.ShippingAddress.City,
                        StateProvince = model.ShippingAddress.StateProvince,
                        ZipPostalCode = model.ShippingAddress.ZipPostalCode,
                        Country = model.ShippingAddress.Country,
                        PhoneNumber = model.ShippingAddress.PhoneNumber,
                        IsDefault = addressCount == 0, // First address is default
                        CreatedAt = DateTime.UtcNow
                    };
                    await _context.UserAddresses.AddAsync(newAddress);
                }
            }

            // Create new Order
            var order = new Order
            {
                UserId = userId,
                TotalAmount = totalAmount,
                OrderDate = DateTime.UtcNow,
                Status = "Pending",
                ShippingAddress = $"{model.ShippingAddress.AddressLine1}, {model.ShippingAddress.City}, {model.ShippingAddress.StateProvince} {model.ShippingAddress.ZipPostalCode}, {model.ShippingAddress.Country}"
            };

            await _context.Orders.AddAsync(order);
            await _context.SaveChangesAsync(); // Save to get the Order ID

            // Create OrderItems and log UserInteractions for each item
            foreach (var cartItem in cartItems)
            {
                // Create OrderItem
                var orderItem = new OrderItem
                {
                    OrderId = order.Id,
                    ProductId = cartItem.ProductId,
                    Quantity = cartItem.Quantity,
                    PriceAtPurchase = cartItem.Product?.Price ?? 0
                };
                await _context.OrderItems.AddAsync(orderItem);

                // AI Data Logging: Log "Purchase" interaction for each item
                var interaction = new UserInteraction
                {
                    UserId = userId,
                    ProductId = cartItem.ProductId,
                    InteractionType = "Purchase",
                    TimeStamp = DateTime.UtcNow
                };
                await _context.UserInteractions.AddAsync(interaction);
            }

            // Remove all CartItems for this user
            _context.CartItems.RemoveRange(cartItems);

            await _context.SaveChangesAsync();

            TempData["Success"] = "Your order has been placed successfully!";
            return RedirectToAction("Confirmation", new { id = order.Id });
        }

        // GET: Checkout/Confirmation/{id}
        [Authorize]
        public async Task<IActionResult> Confirmation(int id)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);

            var order = await _context.Orders
                .Include(o => o.OrderItems)
                .ThenInclude(oi => oi.Product)
                .FirstOrDefaultAsync(o => o.Id == id && o.UserId == userId);

            if (order == null)
            {
                return NotFound();
            }

            var confirmation = new OrderConfirmation
            {
                OrderId = order.Id,
                OrderDate = order.OrderDate,
                TotalAmount = order.TotalAmount,
                Status = order.Status,
                EstimatedDelivery = order.OrderDate.AddDays(5),
                Items = order.OrderItems.Select(oi => new CartItemViewModel
                {
                    ProductId = oi.ProductId,
                    ProductName = oi.Product?.Name ?? "Unknown",
                    Price = oi.PriceAtPurchase,
                    Quantity = oi.Quantity,
                    ImageUrl = oi.Product?.ImageUrl
                }).ToList()
            };

            return View(confirmation);
        }

        // POST: Checkout/ValidateAddress
        [HttpPost]
        public IActionResult ValidateAddress([FromBody] ShippingAddress address)
        {
            if (string.IsNullOrWhiteSpace(address.FirstName) ||
                string.IsNullOrWhiteSpace(address.LastName))
            {
                return Json(new { success = false, message = "Name is required" });
            }

            return Json(new { success = true, message = "Address is valid" });
        }

        // POST: Checkout/CalculateShipping
        [HttpPost]
        [Authorize]
        public async Task<IActionResult> CalculateShipping([FromBody] ShippingAddress address)
        {
            var userId = User.FindFirstValue(ClaimTypes.NameIdentifier);
            decimal cartTotal = 0;

            if (!string.IsNullOrEmpty(userId))
            {
                cartTotal = await _context.CartItems
                    .Include(c => c.Product)
                    .Where(c => c.UserId == userId)
                    .SumAsync(c => (c.Product != null ? c.Product.Price : 0) * c.Quantity);
            }

            // Free shipping for orders over $100
            decimal shippingCost = cartTotal >= 100 ? 0 : 10.00m;

            return Json(new
            {
                success = true,
                shippingCost = shippingCost,
                estimatedDays = 5
            });
        }

        // POST: Checkout/ProcessPayment
        [HttpPost]
        public IActionResult ProcessPayment([FromBody] PaymentInfo payment)
        {
            if (string.IsNullOrWhiteSpace(payment.CardNumber))
            {
                return Json(new { success = false, message = "Card number is required" });
            }

            // Simulate payment processing
            var transactionId = Guid.NewGuid().ToString();

            return Json(new
            {
                success = true,
                transactionId = transactionId,
                message = "Payment processed successfully"
            });
        }

        // POST: Checkout/ApplyPromoCode
        [HttpPost]
        public IActionResult ApplyPromoCode([FromBody] PromoCodeRequest request)
        {
            var validCodes = new Dictionary<string, decimal>
            {
                { "SAVE10", 10.00m },
                { "SAVE20", 20.00m },
                { "FREESHIP", 10.00m }
            };

            if (validCodes.ContainsKey(request.Code.ToUpper()))
            {
                var discount = validCodes[request.Code.ToUpper()];
                return Json(new
                {
                    success = true,
                    discount = discount,
                    message = $"Promo code applied! You saved ${discount:F2}"
                });
            }

            return Json(new
            {
                success = false,
                message = "Invalid promo code"
            });
        }
    }

    // Request models for API endpoints
    public class PromoCodeRequest
    {
        public string Code { get; set; } = string.Empty;
    }
}
