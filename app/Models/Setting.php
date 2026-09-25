<?php
namespace App\Models;
use Illuminate\Database\Eloquent\Model;
class Setting extends Model {
    public $timestamps = false;
    public $incrementing = false;
    protected $primaryKey = 'key';
    protected $keyType = 'string';
    protected $guarded = [];
    public static function values(): array {
        return array_replace(['name'=>'Ma’had Aly','tagline'=>'Merawat tradisi, menjawab zaman.','location'=>'Situbondo',
            'about'=>'Ruang kajian fiqih kontemporer, khazanah pesantren, dan gagasan keislaman dari Situbondo.',
            'editorial'=>'Susunan redaksi akan diumumkan oleh pengelola media.','email'=>''],static::pluck('value','key')->all());
    }
}
