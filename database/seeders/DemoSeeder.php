<?php
namespace Database\Seeders;
use Illuminate\Database\Seeder;
use App\Models\{User,Article,Category};
use Illuminate\Support\Str;
class DemoSeeder extends Seeder {
    public function run(): void {
        if (app()->isProduction() || !config('media.demo')) throw new \RuntimeException('DemoSeeder hanya boleh berjalan di development dengan MEDIA_DEMO=true.');
        $this->call(DatabaseSeeder::class);
        $author=User::firstOrCreate(['email'=>'contoh@media.invalid'],['name'=>'Redaksi Demo','password'=>Str::random(50)]);
        $author->active=false; $author->save();
        $topics=[
            ['Membaca zaman, merawat tradisi: fiqih dalam kehidupan digital','fiqih-kontemporer','Ruang untuk menelaah perubahan, mengajukan pertanyaan, dan mempertemukan khazanah pesantren dengan kehidupan sehari-hari.'],
            ['Bahtsul masail: ketika pertanyaan menjadi jalan belajar','bahtsul-masail','Mengenal ruang musyawarah dan pentingnya memeriksa sumber sebelum merumuskan jawaban.'],
            ['Kitab kuning dan tradisi berpikir yang terus hidup','khazanah','Catatan pengantar tentang membaca teks, memahami konteks, dan merawat ketelitian dalam belajar.'],
            ['Menjaga adab di tengah derasnya arus informasi','opini','Gagasan tentang tanggung jawab berbagi informasi dan membangun percakapan yang saling menghormati.'],
            ['Dari ruang belajar menuju ruang pengabdian','kabar-mahad','Contoh rubrik untuk dokumentasi kegiatan dan cerita kehidupan di lingkungan Ma’had Aly.'],
            ['Ekologi sebagai ruang kajian bersama pesantren','fiqih-kontemporer','Usulan tema diskusi tentang lingkungan, kehidupan masyarakat, dan tanggung jawab bersama.'],
            ['Menulis adalah cara lain merawat ingatan','opini','Menghadirkan pengalaman belajar sebagai catatan yang bermanfaat bagi pembaca.'],
        ];
        foreach ($topics as $i=>[$title,$slug,$excerpt]) {
            $a=Article::firstOrCreate(['slug'=>'demo-'.($i+1)],['author_id'=>$author->id,'featured'=>$i===0]);
            if ($a->revisions()->exists()) continue;
            $rev=$a->revisions()->create(['category_id'=>Category::where('slug',$slug)->value('id'),'title'=>$title,'excerpt'=>$excerpt,
                'body'=>"**Catatan: tulisan ini merupakan konten contoh untuk menguji tampilan development. Bukan berita kegiatan, fatwa, atau pernyataan resmi lembaga.**\n\n".$excerpt."\n\n## Membuka ruang pertanyaan\n\nKehidupan berubah dan menghadirkan pertanyaan baru. Di lingkungan pesantren, pertanyaan dapat menjadi titik berangkat untuk membaca, berdiskusi, dan mencari rujukan yang dapat diperiksa bersama.\n\nProses penyusunan kajian perlu membedakan gambaran masalah, teks rujukan, dan kesimpulan penulis. Pemisahan ini membantu pembaca memahami bagaimana sebuah gagasan dirumuskan.\n\n## Ketelitian sebelum publikasi\n\nNaskah kajian perlu menyertakan rujukan lengkap: penulis, judul, edisi, halaman, serta konteks kutipan. Penyebutan hasil bahtsul masail juga memerlukan dokumen dan verifikasi pihak yang berwenang.\n\n> Ruang redaksi adalah tempat gagasan diperiksa sebelum dipertemukan dengan pembaca.\n\nContoh artikel ini menunjukkan letak judul, ringkasan, paragraf, subjudul, kutipan, dan catatan rujukan. Ganti seluruh konten contoh dengan naskah terverifikasi sebelum digunakan sebagai publikasi lembaga.",
                'sources'=>'Konten demonstrasi. Tidak mengutip kitab atau menetapkan hukum. Redaksi wajib mengisi rujukan terverifikasi pada naskah yang sebenarnya.',
                'status'=>'published','cover_path'=>$i===0 || $i===2 ? 'demo:library' : null,
                'cover_caption'=>$i===0 || $i===2 ? 'Ilustrasi editorial dibuat dengan AI; bukan foto lokasi Ma’had Aly.' : null,
                'approved_at'=>now()->subHours($i+1),'publish_at'=>now()->subHours($i+1)]);
            $a->update(['published_revision_id'=>$rev->id,'published_at'=>now()->subHours($i+1)]);
        }
    }
}
