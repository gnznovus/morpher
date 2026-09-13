<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_REST {
    const NAMESPACE = 'morpher/v1';

    private $deployments;

    public function __construct( Morpher_Deployment $deployments ) {
        $this->deployments = $deployments;
    }

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

        register_rest_route(
            self::NAMESPACE,
            '/deployments',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( $this, 'deployments' ),
                'permission_callback' => array( $this, 'manage_options_permission' ),
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
                    'deployments:list',
                ),
            )
        );
    }

    public function deployments() {
        $items = array_map(
            function ( $row ) {
                return array(
                    'deployment'  => isset( $row['deployment'] ) ? (string) $row['deployment'] : '',
                    'slug'        => isset( $row['slug'] ) ? (string) $row['slug'] : '',
                    'title'       => isset( $row['title'] ) ? (string) $row['title'] : '',
                    'status'      => isset( $row['status'] ) ? (string) $row['status'] : '',
                    'template_id' => isset( $row['id'] ) ? (int) $row['id'] : 0,
                    'error'       => isset( $row['error'] ) ? (string) $row['error'] : '',
                );
            },
            $this->deployments->rows()
        );

        return rest_ensure_response(
            array(
                'deployments' => array_values( $items ),
            )
        );
    }

    public function manage_options_permission() {
        if ( current_user_can( 'manage_options' ) ) {
            return true;
        }

        return new WP_Error(
            'morpher_rest_forbidden',
            'You are not allowed to manage Morpher deployments.',
            array( 'status' => rest_authorization_required_code() )
        );
    }
}
