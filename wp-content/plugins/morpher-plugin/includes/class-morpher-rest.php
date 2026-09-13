<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_REST {
    const NAMESPACE = 'morpher/v1';

    public function register() {
        add_action( 'rest_api_init', array( $this, 'register_routes' ) );
    }

    public function register_routes() {
        register_rest_route(
            self::NAMESPACE,
            '/health',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( $this, 'health' ),
                'permission_callback' => '__return_true',
            )
        );
    }

    public function health() {
        $elementor_ready = did_action( 'elementor/loaded' ) || class_exists( '\\Elementor\\Plugin' );

        return rest_ensure_response(
            array(
                'status'       => 'ok',
                'service'      => 'morpher-wordpress',
                'api_version'  => 'v1',
                'plugin'       => array(
                    'version' => defined( 'MORPHER_PLUGIN_VERSION' ) ? MORPHER_PLUGIN_VERSION : null,
                ),
                'wordpress'    => array(
                    'version' => get_bloginfo( 'version' ),
                    'site_url' => get_site_url(),
                ),
                'integrations' => array(
                    'elementor' => array(
                        'ready'   => $elementor_ready,
                        'version' => defined( 'ELEMENTOR_VERSION' ) ? ELEMENTOR_VERSION : null,
                    ),
                ),
                'capabilities' => array(
                    'health',
                ),
            )
        );
    }
}
