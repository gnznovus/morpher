<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Auth {
    const TOKEN_OPTION      = 'morpher_connection_token_hash';
    const PAIRING_TRANSIENT = 'morpher_pairing_session';
    const PAIRING_TTL       = 300;
    const MAX_ATTEMPTS      = 5;

    public function start_pairing() {
        $code = str_pad( (string) random_int( 0, 999999 ), 6, '0', STR_PAD_LEFT );

        set_transient(
            self::PAIRING_TRANSIENT,
            array(
                'code_hash'  => wp_hash_password( $code ),
                'attempts'   => 0,
                'expires_at' => time() + self::PAIRING_TTL,
            ),
            self::PAIRING_TTL
        );

        return array(
            'code'       => $code,
            'expires_in' => self::PAIRING_TTL,
        );
    }

    public function complete_pairing( $code, $token ) {
        $session = get_transient( self::PAIRING_TRANSIENT );

        if ( ! is_array( $session ) || empty( $session['code_hash'] ) ) {
            return new WP_Error(
                'morpher_pairing_unavailable',
                'No active Morpher pairing session was found.',
                array( 'status' => 400 )
            );
        }

        $attempts = isset( $session['attempts'] ) ? (int) $session['attempts'] : 0;
        if ( $attempts >= self::MAX_ATTEMPTS ) {
            delete_transient( self::PAIRING_TRANSIENT );
            return new WP_Error(
                'morpher_pairing_locked',
                'Morpher pairing expired after too many failed attempts.',
                array( 'status' => 429 )
            );
        }

        $session['attempts'] = $attempts + 1;
        $remaining           = max( 1, (int) $session['expires_at'] - time() );
        set_transient( self::PAIRING_TRANSIENT, $session, $remaining );

        if ( ! wp_check_password( (string) $code, (string) $session['code_hash'] ) ) {
            return new WP_Error(
                'morpher_pairing_code_invalid',
                'The Morpher pairing code is invalid.',
                array( 'status' => 401 )
            );
        }

        if ( ! $this->is_valid_token( $token ) ) {
            return new WP_Error(
                'morpher_pairing_token_invalid',
                'The Morpher connection token is invalid.',
                array( 'status' => 400 )
            );
        }

        update_option( self::TOKEN_OPTION, wp_hash_password( (string) $token ), false );
        delete_transient( self::PAIRING_TRANSIENT );

        return true;
    }

    public function authenticate_request( WP_REST_Request $request ) {
        $stored_hash = get_option( self::TOKEN_OPTION, '' );
        if ( ! is_string( $stored_hash ) || '' === $stored_hash ) {
            return new WP_Error(
                'morpher_not_connected',
                'This WordPress site is not connected to Morpher.',
                array( 'status' => 401 )
            );
        }

        $authorization = trim( (string) $request->get_header( 'authorization' ) );
        if ( ! preg_match( '/^Bearer\s+(.+)$/i', $authorization, $matches ) ) {
            return new WP_Error(
                'morpher_auth_required',
                'A Morpher bearer token is required.',
                array( 'status' => 401 )
            );
        }

        $token = trim( $matches[1] );
        if ( ! $this->is_valid_token( $token ) || ! wp_check_password( $token, $stored_hash ) ) {
            return new WP_Error(
                'morpher_auth_invalid',
                'The Morpher bearer token is invalid.',
                array( 'status' => 401 )
            );
        }

        return true;
    }

    public function revoke() {
        delete_option( self::TOKEN_OPTION );
        delete_transient( self::PAIRING_TRANSIENT );
    }

    public function is_connected() {
        $stored_hash = get_option( self::TOKEN_OPTION, '' );
        return is_string( $stored_hash ) && '' !== $stored_hash;
    }

    private function is_valid_token( $token ) {
        if ( ! is_string( $token ) ) {
            return false;
        }

        $length = strlen( $token );
        return $length >= 43 && $length <= 128 && 1 === preg_match( '/^[A-Za-z0-9_-]+$/', $token );
    }
}
