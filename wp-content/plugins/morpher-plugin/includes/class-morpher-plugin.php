<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Plugin {
    private $assets;
    private $admin;
    private $rest;

    public function __construct( $plugin_file, $root ) {
        $deployments  = new Morpher_Deployment( trailingslashit( $root ) . 'deployments' );
        $diagnostics  = new Morpher_Diagnostics( $deployments, $root );
        $auth         = new Morpher_Auth();
        $this->assets = new Morpher_Assets( $plugin_file, $root );
        $this->admin  = new Morpher_Admin( $deployments, $diagnostics, $plugin_file );
        $this->rest   = new Morpher_REST( $deployments, $auth );
    }

    public function register() {
        add_action( 'wp_enqueue_scripts', array( $this->assets, 'enqueue_fonts' ), 1 );
        add_action( 'elementor/frontend/after_enqueue_styles', array( $this->assets, 'enqueue_fonts' ), 1 );
        add_action( 'elementor/editor/after_enqueue_styles', array( $this->assets, 'enqueue_fonts' ), 1 );
        add_action( 'elementor/preview/enqueue_styles', array( $this->assets, 'enqueue_fonts' ), 1 );

        $this->admin->register();
        $this->rest->register();
    }
}
