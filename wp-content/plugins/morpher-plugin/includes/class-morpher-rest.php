<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_REST {
    const NAMESPACE = 'morpher/v1';

    private $deployments;
    private $auth;

    public function __construct( Morpher_Deployment $deployments, Morpher_Auth $auth ) {
        $this->deployments = $deployments;
        $this->auth        = $auth;
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
            '/pairing/start',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( $this, 'pairing_start' ),
                'permission_callback' => array( $this, 'manage_options_permission' ),
            )
        );

        register_rest_route(
            self::NAMESPACE,
            '/pairing/complete',
            array(
                'methods'             => WP_REST_Server::CREATABLE,
                'callback'            => array( $this, 'pairing_complete' ),
                'permission_callback' => '__return_true',
            )
        );

        register_rest_route(
            self::NAMESPACE,
            '/deployments',
            array(
                'methods'             => WP_REST_Server::READABLE,
                'callback'            => array( $this, 'deployments' ),
                'permission_callback' => array( $this, 'morpher_auth_permission' ),
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
                'connection'   => array(
                    'paired' => $this->auth->is_connected(),
                ),
                'capabilities' => array(
                    'health',
                    'pairing',
                    'deployments:list',
                ),
            )
        );
    }

    public function pairing_start() {
        return rest_ensure_response( $this->auth->start_pairing() );
    }

    public function pairing_complete( WP_REST_Request $request ) {
        $params = $request->get_json_params();
        $code   = isset( $params['code'] ) ? trim( (string) $params['code'] ) : '';
        $token  = isset( $params['token'] ) ? trim( (string) $params['token'] ) : '';

        if ( ! preg_match( '/^\d{6}$/', $code ) ) {
            return new WP_Error(
                'morpher_pairing_code_invalid',
                'A six-digit Morpher pairing code is required.',
                array( 'status' => 400 )
            );
        }

        $result = $this->auth->complete_pairing( $code, $token );
        if ( is_wp_error( $result ) ) {
            return $result;
        }

        return rest_ensure_response(
            array(
                'status'    => 'connected',
                'site_url'  => get_site_url(),
                'api_version' => 'v1',
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

    public function morpher_auth_permission( WP_REST_Request $request ) {
        return $this->auth->authenticate_request( $request );
    }

    public function manage_options_permission() {
        if ( current_user_can( 'manage_options' ) ) {
            return true;
        }

        return new WP_Error(
            'morpher_rest_forbidden',
            'You are not allowed to manage Morpher pairing.',
            array( 'status' => rest_authorization_required_code() )
        );
    }
}
