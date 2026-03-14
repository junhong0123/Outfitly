import re

with open('c:/Users/User/source/repos/Outfitly/Data/ApplicationDbContext.cs', 'r', encoding='utf-8') as f:
    content = f.read()

# Add DbSet for ProductSize
content = content.replace("public DbSet<Product> Products { get; set; } = default!;", 
                          "public DbSet<Product> Products { get; set; } = default!;\n        public DbSet<ProductSize> ProductSizes { get; set; } = default!;")

# Replace Property configurations
old_config = """            // Configure Product -> Colors/Sizes as JSON (for EF Core 9)
            modelBuilder.Entity<Product>()
                .Property(p => p.AvailableColors)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());

            modelBuilder.Entity<Product>()
                .Property(p => p.AvailableSizes)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());"""

new_config = """            // Configure Product -> Colors/Images as strings
            modelBuilder.Entity<Product>()
                .Property(p => p.AvailableColors)
                .HasConversion(
                    v => string.Join(',', v.Select(c => c.ToString())),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).Select(c => Enum.Parse<Color>(c)).ToList());

            modelBuilder.Entity<Product>()
                .Property(p => p.ImageUrls)
                .HasConversion(
                    v => string.Join(',', v),
                    v => v.Split(',', StringSplitOptions.RemoveEmptyEntries).ToList());"""

content = content.replace(old_config, new_config)

# Extract product blocks to generate ProductSizes and fix Product properties
product_blocks = re.findall(r'new Product\s*\{([^}]*)\}', content)

product_sizes_seed = []
size_id = 1

for block in product_blocks:
    # get Id
    product_id_match = re.search(r'Id\s*=\s*(\d+)', block)
    if not product_id_match: continue
    product_id = int(product_id_match.group(1))
    
    # get StockQuantity
    qty_match = re.search(r'StockQuantity\s*=\s*(\d+)', block)
    qty = int(qty_match.group(1)) if qty_match else 0
    
    # get AvailableSizes
    sizes_match = re.search(r'AvailableSizes\s*=\s*new List<string> \{([^}]+)\}', block)
    if sizes_match:
        sizes = [s.strip().strip('"') for s in sizes_match.group(1).split(',')]
        # distribute qty among sizes
        base_qty = qty // len(sizes)
        rem = qty % len(sizes)
        
        for i, s in enumerate(sizes):
            q = base_qty + (1 if i < rem else 0)
            product_sizes_seed.append(f"""                new ProductSize {{ Id = {size_id}, ProductId = {product_id}, Size = "{s}", Quantity = {q} }}""")
            size_id += 1

# Now replace the inner parts of the Product initializers
# 1. AvailableColors = new List<string> { "White", "Black" } -> AvailableColors = new List<Color> { Color.White, Color.Black }
def replace_colors(match):
    colors_str = match.group(1)
    # properly map strings to Enums, some colors might have spaces or slashes which aren't valid enums
    # Let's clean them up: "Navy/White" -> Navy, etc. Just drop unsupported or pick exact ones.
    # The user has: White, Black, Gray, Blue, Navy, Olive, Red, Pink, Yellow, Beige, Brown, Tan, Camel, Cream, Burgundy, Emerald, Cognac, Khaki
    # Let's map complex ones to simple ones
    def clean_color(c):
        c = c.strip().strip('"')
        if "/" in c: c = c.split("/")[0]
        return f"Color.{c}"
    
    colors = [clean_color(c) for c in colors_str.split(',')]
    return f"AvailableColors = new List<Color> {{ {', '.join(colors)} }}"

content = re.sub(r'AvailableColors\s*=\s*new List<string> \{([^}]+)\}', replace_colors, content)

# 2. AvailableSizes = ... (Remove it)
content = re.sub(r'\s*AvailableSizes\s*=\s*new List<string> \{[^}]+\},', '', content)

# 3. StockQuantity = ... (Remove it)
content = re.sub(r'\s*StockQuantity\s*=\s*\d+,', '', content)

# 4. ImageUrl = "..." -> ImageUrls = new List<string> { "..." }
content = re.sub(r'ImageUrl\s*=\s*("[^"]+")', r'ImageUrls = new List<string> { \1 }', content)

# Add ProductSize seed data
seed_data_block = f"""
            // Seed ProductSizes
            modelBuilder.Entity<ProductSize>().HasData(
{',\n'.join(product_sizes_seed)}
            );
"""

# insert right before the last closing brace pair
content = content.replace("            );\n        }\n    }\n}", f"            );\n{seed_data_block}        }}\n    }}\n}}")

with open('c:/Users/User/source/repos/Outfitly/Data/ApplicationDbContext.cs', 'w', encoding='utf-8') as f:
    f.write(content)

print("ApplicationDbContext.cs updated successfully.")
