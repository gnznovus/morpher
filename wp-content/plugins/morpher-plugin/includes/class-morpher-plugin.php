<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Plugin {
    private $assets;
    private $admin;
    private $pairing_admin;
    private $rest;

    public function __construct( $plugin_file, $root ) {
        $deployments          = new Morpher_Deployment( trailingslashit( $root ) . 'deployments' );
        $diagnostics          = new Morpher_Diagnostics( $deployments, $root );
        $auth                 = new Morpher_Auth();
        $acknowledgements     = new Morpher_Acknowledgements();
        $this->assets         = new Morpher_Assets( $plugin_file, $root );
        $this->admin          = new Morpher_Admin( $deployments, $diagnostics, $plugin_file );
        $this->pairing_admin  = new Morpher_Pairing_Admin( $auth );
        $this->rest           = new Morpher_REST( $deployments, $auth, $acknowledgements );
    }

    public function register() {
        add_action( 'wp_enqueue_scripts', array( $this->assets, 'enqueue_fonts' ), 1 );
        add_action( 'elementor/frontend/after_enqueue_styles', array( $this->assets, 'enqueue_fonts' ), 1 );
        add_action( 'elementor/editor/after_enqueue_styles', array( $this->assets, 'enqueue_fonts' ), 1 );
        add_action( 'elementor/preview/enqueue_styles', array( $this->assets, 'enqueue_fonts' ), 1 );

        $this->admin->register();
        $this->pairing_admin->register();
        $this->rest->register();
    }
}
