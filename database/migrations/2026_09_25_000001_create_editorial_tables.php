<?php
use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;
return new class extends Migration {
    public function up(): void {
        Schema::table('users', function (Blueprint $t) {
            $t->string('role')->default('contributor'); $t->boolean('active')->default(true);
        });
        Schema::create('categories', function (Blueprint $t) {
            $t->id(); $t->string('name'); $t->string('slug')->unique(); $t->text('description')->nullable(); $t->timestamps();
        });
        Schema::create('articles', function (Blueprint $t) {
            $t->id(); $t->foreignId('author_id')->constrained('users'); $t->string('slug')->unique();
            $t->unsignedBigInteger('published_revision_id')->nullable()->index(); $t->boolean('featured')->default(false);
            $t->timestamp('published_at')->nullable()->index(); $t->timestamps();
        });
        Schema::create('revisions', function (Blueprint $t) {
            $t->id(); $t->foreignId('article_id')->constrained()->cascadeOnDelete(); $t->foreignId('category_id')->constrained();
            $t->string('title'); $t->text('excerpt'); $t->longText('body'); $t->text('sources')->nullable();
            $t->string('cover_path')->nullable(); $t->string('cover_caption')->nullable();
            $t->string('status')->default('draft')->index(); $t->text('review_note')->nullable();
            $t->foreignId('reviewed_by')->nullable()->constrained('users'); $t->timestamp('approved_at')->nullable();
            $t->timestamp('publish_at')->nullable()->index(); $t->timestamps();
        });
        Schema::create('audit_logs', function (Blueprint $t) {
            $t->id(); $t->foreignId('user_id')->nullable()->constrained(); $t->foreignId('article_id')->nullable()->constrained();
            $t->foreignId('revision_id')->nullable()->constrained(); $t->string('action'); $t->text('note')->nullable(); $t->timestamps();
        });
        Schema::create('settings', function (Blueprint $t) { $t->string('key')->primary(); $t->text('value')->nullable(); });
    }
    public function down(): void {
        Schema::dropIfExists('audit_logs'); Schema::dropIfExists('revisions'); Schema::dropIfExists('articles');
        Schema::dropIfExists('categories'); Schema::dropIfExists('settings');
        Schema::table('users', fn (Blueprint $t) => $t->dropColumn(['role','active']));
    }
};
