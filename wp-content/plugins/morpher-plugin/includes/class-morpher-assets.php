<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Assets {
    private $plugin_file;
    private $root;

    public function __construct( $plugin_file, $root ) {
        $this->plugin_file = $plugin_file;
        $this->root        = untrailingslashit( $root );
    }

    public function enqueue_fonts() {
        $css_path = trailingslashit( $this->root ) . 'assets/fonts.css';
        if ( ! file_exists( $css_path ) ) {
            return;
        }

        wp_enqueue_style(
            'morpher-fonts',
            plugin_dir_url( $this->plugin_file ) . 'assets/fonts.css',
            array(),
            (string) filemtime( $css_path )
        );
    }
}
