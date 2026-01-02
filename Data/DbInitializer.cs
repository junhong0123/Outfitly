using Microsoft.AspNetCore.Identity;
using Microsoft.EntityFrameworkCore;
using Outfitly.Models;

namespace Outfitly.Data
{
    public static class DbInitializer
    {
        public static async Task InitializeAsync(IServiceProvider serviceProvider)
        {
            using var context = serviceProvider.GetRequiredService<ApplicationDbContext>();
            var userManager = serviceProvider.GetRequiredService<UserManager<IdentityUser>>();
            var roleManager = serviceProvider.GetRequiredService<RoleManager<IdentityRole>>();

            // Ensure database is created
            await context.Database.MigrateAsync();

            // Create Admin role if it doesn't exist
            if (!await roleManager.RoleExistsAsync("Admin"))
            {
                await roleManager.CreateAsync(new IdentityRole("Admin"));
            }

            // Create admin user if it doesn't exist
            var adminEmail = "admin@outfitly.com";
            var adminUser = await userManager.FindByEmailAsync(adminEmail);
            if (adminUser == null)
            {
                adminUser = new IdentityUser
                {
                    UserName = adminEmail,
                    Email = adminEmail,
                    EmailConfirmed = true
                };

                var result = await userManager.CreateAsync(adminUser, "Admin@123");
                if (result.Succeeded)
                {
                    await userManager.AddToRoleAsync(adminUser, "Admin");
                }
            }

            // Seed products if database is empty
            if (!await context.Products.AnyAsync())
            {
                var products = new List<Product>
                {
                    new Product
                    {
                        Name = "Minimal Cotton Tee",
                        Price = 49.00m,
                        Description = "Premium quality cotton t-shirt with a minimalist design. Perfect for everyday wear.",
                        Category = "tops",
                        Stock = 50,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Tailored Linen Pants",
                        Price = 89.00m,
                        Description = "Comfortable and breathable linen pants with a tailored fit.",
                        Category = "bottoms",
                        Stock = 30,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Leather Crossbody Bag",
                        Price = 129.00m,
                        Description = "Genuine leather crossbody bag with multiple compartments.",
                        Category = "accessories",
                        Stock = 20,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Classic Wool Coat",
                        Price = 249.00m,
                        Description = "Elegant wool coat for cold weather. Timeless design.",
                        Category = "outerwear",
                        Stock = 15,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Silk Blend Blouse",
                        Price = 79.00m,
                        Description = "Luxurious silk blend blouse with a flowing silhouette.",
                        Category = "tops",
                        Stock = 40,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Denim Jacket",
                        Price = 119.00m,
                        Description = "Classic denim jacket with a modern fit. A wardrobe essential.",
                        Category = "outerwear",
                        Stock = 35,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Wide Leg Trousers",
                        Price = 95.00m,
                        Description = "Trendy wide leg trousers in a comfortable fabric.",
                        Category = "bottoms",
                        Stock = 25,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Cashmere Sweater",
                        Price = 159.00m,
                        Description = "Soft cashmere sweater for ultimate comfort and warmth.",
                        Category = "tops",
                        Stock = 18,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Ankle Boots",
                        Price = 189.00m,
                        Description = "Stylish ankle boots made from premium leather.",
                        Category = "accessories",
                        Stock = 22,
                        ImageUrl = null
                    },
                    new Product
                    {
                        Name = "Oversized Blazer",
                        Price = 199.00m,
                        Description = "On-trend oversized blazer that pairs well with any outfit.",
                        Category = "outerwear",
                        Stock = 12,
                        ImageUrl = null
                    }
                };

                await context.Products.AddRangeAsync(products);
                await context.SaveChangesAsync();
            }
        }
    }
}
