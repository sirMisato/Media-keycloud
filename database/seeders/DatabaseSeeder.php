<?php
namespace Database\Seeders;
use Illuminate\Database\Seeder;
use App\Models\Category;
class DatabaseSeeder extends Seeder {
    public function run(): void {
        foreach ([
            ['Fiqih Kontemporer','fiqih-kontemporer','Membaca persoalan hari ini melalui khazanah fiqih dan telaah keilmuan.'],
            ['Bahtsul Masail','bahtsul-masail','Ruang musyawarah, telaah rujukan, dan pendalaman persoalan umat.'],
            ['Khazanah','khazanah','Mengenal pemikiran, kitab, dan tradisi keilmuan pesantren.'],
            ['Opini','opini','Gagasan dan perspektif dari ruang belajar hingga kehidupan masyarakat.'],
            ['Kabar Ma’had','kabar-mahad','Kabar pendidikan, kegiatan, dan kehidupan lingkungan Ma’had Aly.'],
        ] as [$name,$slug,$description]) Category::firstOrCreate(['slug'=>$slug],compact('name','description'));
    }
}
