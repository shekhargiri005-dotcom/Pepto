"""
services/product_service.py — Product catalog management and search.
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from python_slugify import slugify
from sqlalchemy import or_, desc, asc, and_

from app.extensions import db
from app.models.product import Product, ProductCategory
from app.models.store import Store
from app.models.pet import Pet
from app.utils.exceptions import NotFoundError, ValidationError, AuthorizationError

logger = logging.getLogger(__name__)


class ProductService:

    # ── Search ────────────────────────────────────────────────────────────────

    def search_products(
        self,
        q: Optional[str] = None,
        species: Optional[str] = None,
        category: Optional[str] = None,
        brand: Optional[str] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_rating: Optional[float] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        per_page: int = 20,
        sort: str = "relevance",
    ) -> Dict:
        query = Product.query.filter_by(is_available=True)

        # Join store to filter unverified stores
        query = query.join(Store).filter(Store.is_verified == True)

        if q:
            search_term = f"%{q}%"
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Product.brand.ilike(search_term),
                    Product.description.ilike(search_term),
                )
            )
        if species:
            # JSONB containment query: suitable_for->species contains the value
            query = query.filter(
                Product.suitable_for["species"].astext.contains(species)
            )
        if category:
            try:
                query = query.filter(Product.category == ProductCategory(category))
            except ValueError:
                pass
        if brand:
            query = query.filter(Product.brand.ilike(f"%{brand}%"))
        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if min_rating is not None:
            query = query.filter(Product.avg_rating >= min_rating)
        if store_id:
            query = query.filter(Product.store_id == store_id)

        # Sorting
        sort_map = {
            "price_asc": asc(Product.price),
            "price_desc": desc(Product.price),
            "rating": desc(Product.avg_rating),
            "popularity": desc(Product.total_reviews),
        }
        query = query.order_by(sort_map.get(sort, desc(Product.avg_rating)))

        pagination = query.paginate(page=page, per_page=min(per_page, 50), error_out=False)
        return {
            "items": [self._product_summary(p) for p in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "pages": pagination.pages,
            "has_next": pagination.has_next,
        }

    def get_store_products(self, store_id: str, page: int = 1, category: Optional[str] = None) -> Dict:
        query = Product.query.filter_by(store_id=store_id)
        if category:
            try:
                query = query.filter(Product.category == ProductCategory(category))
            except ValueError:
                pass
        pagination = query.order_by(Product.name).paginate(page=page, per_page=50, error_out=False)
        return {
            "items": [self._product_detail(p) for p in pagination.items],
            "total": pagination.total,
            "page": pagination.page,
            "has_next": pagination.has_next,
        }

    def get_product(self, product_id: str) -> Dict:
        product = Product.query.get(product_id)
        if not product:
            raise NotFoundError("Product not found")
        return self._product_detail(product)

    def get_recommended(self, customer_id: str) -> List[Dict]:
        """Return products matching the species of the customer's registered pets."""
        pets = Pet.query.filter_by(customer_id=customer_id, is_active=True).all()
        species_list = list({p.species.value for p in pets if p.species}) if pets else ["dog"]

        products = Product.query.join(Store).filter(
            Store.is_verified == True,
            Product.is_available == True,
            Product.avg_rating >= 3.5,
        ).order_by(desc(Product.avg_rating)).limit(20).all()

        # Filter by matching species in suitable_for JSONB
        matched = []
        for p in products:
            suitable = p.suitable_for or {}
            product_species = suitable.get("species", [])
            if any(s in product_species for s in species_list):
                matched.append(self._product_summary(p))

        return matched[:12]

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_product(self, owner_id: str, data: dict) -> Dict:
        store = Store.query.filter_by(owner_id=owner_id).first()
        if not store:
            raise ValidationError("You must create a store before adding products")

        name = data.get("name", "").strip()
        price = data.get("price")
        if not name:
            raise ValidationError("Product name is required")
        if price is None or float(price) <= 0:
            raise ValidationError("Price must be greater than zero")

        slug = slugify(name)
        base_slug = slug
        counter = 1
        while Product.query.filter_by(store_id=str(store.id), slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        product = Product(
            store_id=str(store.id),
            name=name,
            slug=slug,
            brand=data.get("brand"),
            category=data.get("category", "dry_food"),
            subcategory=data.get("subcategory"),
            description=data.get("description"),
            ingredients=data.get("ingredients"),
            nutritional_info=data.get("nutritional_info"),
            suitable_for=data.get("suitable_for"),
            price=price,
            discount_price=data.get("discount_price"),
            unit=data.get("unit", "pack"),
            weight_grams=data.get("weight_grams"),
            stock_quantity=data.get("stock_quantity", 0),
            images=data.get("images", []),
        )
        db.session.add(product)
        db.session.commit()
        logger.info("Product created: %s in store %s", product.id, store.id)
        return self._product_detail(product)

    def update_product(self, owner_id: str, product_id: str, data: dict) -> Dict:
        product = self._get_owned_product(owner_id, product_id)
        updatable = [
            "name", "brand", "description", "ingredients", "nutritional_info",
            "suitable_for", "price", "discount_price", "unit", "weight_grams",
            "is_available", "images", "subcategory",
        ]
        for field in updatable:
            if field in data:
                setattr(product, field, data[field])
        db.session.commit()
        return self._product_detail(product)

    def delete_product(self, owner_id: str, product_id: str) -> None:
        product = self._get_owned_product(owner_id, product_id)
        db.session.delete(product)
        db.session.commit()

    def update_stock(self, owner_id: str, product_id: str, quantity: int, reason: Optional[str] = None) -> Dict:
        product = self._get_owned_product(owner_id, product_id)
        if quantity is None or quantity < 0:
            raise ValidationError("Quantity must be a non-negative integer")
        product.stock_quantity = quantity
        product.is_available = quantity > 0
        db.session.commit()
        logger.info("Stock updated: product %s → %d units (%s)", product_id, quantity, reason)
        return self._product_detail(product)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_owned_product(self, owner_id: str, product_id: str) -> Product:
        product = Product.query.get(product_id)
        if not product:
            raise NotFoundError("Product not found")
        store = Store.query.filter_by(id=product.store_id, owner_id=owner_id).first()
        if not store:
            raise AuthorizationError("You do not own this product")
        return product

    def _product_summary(self, p: Product) -> Dict:
        return {
            "id": str(p.id),
            "name": p.name,
            "brand": p.brand,
            "category": p.category.value if p.category else None,
            "price": float(p.price),
            "discount_price": float(p.discount_price) if p.discount_price else None,
            "effective_price": p.effective_price,
            "unit": p.unit,
            "images": p.images or [],
            "avg_rating": p.avg_rating,
            "total_reviews": p.total_reviews,
            "is_available": p.is_available,
            "stock_quantity": p.stock_quantity,
            "store_id": str(p.store_id),
            "suitable_for": p.suitable_for,
        }

    def _product_detail(self, p: Product) -> Dict:
        d = self._product_summary(p)
        d.update({
            "slug": p.slug,
            "description": p.description,
            "ingredients": p.ingredients,
            "nutritional_info": p.nutritional_info,
            "subcategory": p.subcategory,
            "weight_grams": p.weight_grams,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        })
        return d
