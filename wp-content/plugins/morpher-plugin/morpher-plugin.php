<?php
/**
 * Plugin Name: Morpher
 * Description: WordPress integration for Morpher-generated Elementor output.
 * Version: 0.1.0
 */

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

function morpher_plugin_enqueue_fonts() {
    $css_path = plugin_dir_path( __FILE__ ) . 'assets/fonts.css';
    if ( ! file_exists( $css_path ) ) {
        return;
    }

    wp_enqueue_style(
        'morpher-fonts',
        plugin_dir_url( __FILE__ ) . 'assets/fonts.css',
        array(),
        (string) filemtime( $css_path )
    );
}

add_action( 'wp_enqueue_scripts', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/frontend/after_enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/editor/after_enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
add_action( 'elementor/preview/enqueue_styles', 'morpher_plugin_enqueue_fonts', 1 );
