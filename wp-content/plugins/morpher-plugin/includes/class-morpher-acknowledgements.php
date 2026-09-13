<?php

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

class Morpher_Acknowledgements {
    const LATEST_OPTION = 'morpher_latest_acknowledgement';

    public function record( $ref_no, $event, $status, $metadata = array() ) {
        $ref_no = strtoupper( trim( (string) $ref_no ) );
        $event  = strtolower( trim( (string) $event ) );
        $status = strtolower( trim( (string) $status ) );
        $event  = preg_replace( '/[^a-z0-9._:-]/', '', $event );
        $status = preg_replace( '/[^a-z0-9._:-]/', '', $status );

        if ( '' === $ref_no || '' === $event || '' === $status ) {
            return new WP_Error(
                'morpher_ack_invalid',
                'Ref No., event, and status are required.',
                array( 'status' => 400 )
            );
        }

        $record = array(
            'ref_no'      => $ref_no,
            'event'       => $event,
            'status'      => $status,
            'metadata'    => is_array( $metadata ) ? $metadata : array(),
            'received_at' => gmdate( 'c' ),
        );

        update_option( self::LATEST_OPTION, $record, false );
        do_action( 'morpher_acknowledged', $record );

        return $record;
    }

    public function latest() {
        $record = get_option( self::LATEST_OPTION, array() );
        return is_array( $record ) ? $record : array();
    }
}
