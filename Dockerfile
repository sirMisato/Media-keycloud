FROM php:8.3-apache-bookworm AS base
RUN apt-get update && apt-get install -y --no-install-recommends libpq-dev libsqlite3-dev libonig-dev libxml2-dev libzip-dev unzip git libpng-dev libjpeg62-turbo-dev libwebp-dev \
 && docker-php-ext-configure gd --with-jpeg --with-webp \
 && docker-php-ext-install -j$(nproc) pdo_pgsql pdo_sqlite mbstring dom xml bcmath zip gd opcache \
 && a2enmod rewrite headers && rm -rf /var/lib/apt/lists/*
COPY --from=composer:2 /usr/bin/composer /usr/local/bin/composer
WORKDIR /var/www/html
COPY docker/apache.conf /etc/apache2/sites-available/000-default.conf
COPY docker/php.ini /usr/local/etc/php/conf.d/media.ini
COPY docker/entrypoint.sh /usr/local/bin/media-entrypoint
RUN chmod +x /usr/local/bin/media-entrypoint
COPY . .
ENV COMPOSER_ALLOW_SUPERUSER=1
FROM base AS test
RUN composer install --prefer-dist --no-interaction --no-progress --optimize-autoloader
RUN cp .env.example .env && php artisan key:generate && php artisan test
FROM base AS production
RUN composer install --no-dev --prefer-dist --no-interaction --no-progress --optimize-autoloader \
 && mkdir -p storage/framework/cache/data storage/framework/sessions storage/framework/views storage/logs storage/app/private bootstrap/cache \
 && chown -R www-data:www-data storage bootstrap/cache
ENTRYPOINT ["media-entrypoint"]
CMD ["apache2-foreground"]
